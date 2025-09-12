from __future__ import annotations

import os
import shutil
import time
import json
import jwt
from typing import List, Optional

from fastapi import (
    FastAPI, UploadFile, File, HTTPException, Request, Depends
)
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel

from .db import get_db, Base, engine, SessionLocal
import asyncio
from . import crud
from . import models  # <— понадобится для reorder
from .schemas import (
    ConfigOut, ButtonOut, ButtonCreate,
    PageOut, PageCreate, PageUpdate,
    BlockOut, BlockCreate, BlockUpdate,
    UserCreate, UserOut,
    SettingsUpdate,
    ButtonGroupCreate, ButtonGroupUpdate, ButtonGroupOut,
)
from .crud import get_user_by_username, verify_password, ensure_admin_user

# helpers
def _next_button_order(db):
    from . import models
    m = db.query(models.Button.order_index).order_by(models.Button.order_index.desc()).first()
    return (m[0] + 1) if m and m[0] is not None else 1

def _ensure_single_home(db, keep_page_id: int):
    from . import models
    db.query(models.Page).filter(models.Page.id != keep_page_id).update({models.Page.is_home: False})
    db.commit()


# ==============================
# Config / App
# ==============================
SECRET_KEY = "change_me_please"   # поменяйте в проде
ALGORITHM = "HS256"

app = FastAPI(title="Kiosk Admin/API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

BASE_DIR = os.path.dirname(__file__)
MEDIA_DIR = os.path.join(os.path.dirname(BASE_DIR), "media")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(MEDIA_DIR, exist_ok=True)

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# -------------------- Simple in-process event bus (SSE) --------------------
_event_subs: set[asyncio.Queue] = set()

def _publish_event(data: dict):
    for q in list(_event_subs):
        try:
            q.put_nowait(data)
        except Exception:
            pass

@app.get("/events")
async def events(request: Request):
    q: asyncio.Queue = asyncio.Queue(maxsize=32)
    _event_subs.add(q)
    async def gen():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(q.get(), timeout=30)
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # keep-alive comment
                    yield ": ping\n\n"
        finally:
            _event_subs.discard(q)
    return StreamingResponse(gen(), media_type="text/event-stream")


# ==============================
# Auth helpers
# ==============================
def get_token_from_cookie(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    # допускаем "Bearer xxx" или просто "xxx"
    scheme, param = get_authorization_scheme_param(token)
    return param if scheme.lower() == "bearer" else token


def require_user(request: Request, db=Depends(get_db)):
    token = get_token_from_cookie(request)
    if not token:
        raise HTTPException(401, "Unauthorized")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(401, "Invalid token")
    username = payload.get("sub")
    if not username:
        raise HTTPException(401, "Invalid token")
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(401, "User not found")
    return user


# ==============================
# Startup: ensure admin/admin
# ==============================
@app.on_event("startup")
def _startup():
    db = SessionLocal()
    try:
        crud.ensure_button_groups_schema(db)
        crud.ensure_settings_columns(db)
        ensure_admin_user(db, "admin", "admin")
    finally:
        db.close()


# ==============================
# Auth pages & endpoints
# ==============================
class LoginForm(BaseModel):
    username: str
    password: str


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})


@app.post("/auth/login")
async def auth_login(request: Request, db=Depends(get_db)):
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = form.get("password") or ""

    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=401,
        )

    payload = {"sub": user.username, "iat": int(time.time())}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    resp = RedirectResponse(url="/admin", status_code=302)
    # HttpOnly cookie, SameSite=Lax; secure toggle via env SECURE_COOKIES=1
    SECURE_COOKIES = bool(int(os.getenv("SECURE_COOKIES", "0")))
    resp.set_cookie(
        "access_token", f"Bearer {token}",
        httponly=True, samesite="lax", max_age=60*60*8, path="/", secure=SECURE_COOKIES
    )


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("access_token", path="/")
    return resp


# ==============================
# Admin: Users
# ==============================
@app.post("/admin/users", response_model=UserOut)
def create_user_admin(payload: UserCreate, db=Depends(get_db), user=Depends(require_user)):
    # Only admins can create users
    if getattr(user, "role", "admin") != "admin":
        raise HTTPException(403, "Forbidden")
    u = crud.create_user(db, payload.username, payload.password, payload.role or "admin")
    if not u:
        raise HTTPException(409, "User already exists")
    return u


# ==============================
# Admin: Settings (org name, logo)
# ==============================
@app.put("/admin/settings")
def update_settings(payload: SettingsUpdate, db=Depends(get_db), user=Depends(require_user)):
    if getattr(user, "role", "admin") != "admin":
        raise HTTPException(403, "Forbidden")
    s = crud.get_settings(db)
    changed = False
    # Org name
    if payload.org_name is not None:
        s.org_name = payload.org_name
        changed = True
    # Logo path
    if payload.logo_path is not None:
        if not s.theme:
            s.theme = models.Theme()
            db.add(s.theme)
        s.theme.logo_path = payload.logo_path
        changed = True
    # Kiosk exit password (optional)
    if payload.kiosk_exit_password:
        try:
            from .crud import pwd_context
            s.exit_password_hash = pwd_context.hash(payload.kiosk_exit_password)
        except Exception:
            s.exit_password_hash = payload.kiosk_exit_password
        changed = True
    # Weather toggles
    try:
        if payload.show_weather is not None:
            s.show_weather = bool(payload.show_weather)
            changed = True
        if payload.weather_city is not None:
            s.weather_city = (payload.weather_city or "").strip() or None
            changed = True
    except Exception:
        pass
    if changed:
        db.commit(); db.refresh(s)
    # return updated config snapshot (compatible with callers)
    return {
        "org_name": s.org_name,
        "footer_qr_text": s.footer_qr_text,
        "footer_clock_format": s.footer_clock_format,
        "theme": s.theme,
        "show_weather": bool(getattr(s, 'show_weather', False)),
        "weather_city": getattr(s, 'weather_city', None),
    }


# ==============================
# Public API (для киоска)
# ==============================
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config", response_model=ConfigOut)
def get_config(db=Depends(get_db)):
    s = crud.get_settings(db)
    # Seed sample content if available
    try:
        crud.upsert_sample_content(db)
    except Exception:
        pass
    return {
        "org_name": s.org_name,
        "footer_qr_text": s.footer_qr_text,
        "footer_clock_format": s.footer_clock_format,
        "theme": s.theme,
        # extra fields tolerated by clients
        "show_weather": bool(getattr(s, 'show_weather', False)),
        "weather_city": getattr(s, 'weather_city', None),
    }


@app.get("/home/buttons", response_model=List[ButtonOut])
def get_home_buttons(db=Depends(get_db)):
    return crud.get_home_buttons(db)

@app.get("/home/menu")
def get_menu(db=Depends(get_db)):
    return crud.get_menu_tree(db)


@app.get("/pages/{slug}", response_model=PageOut)
def get_page(slug: str, db=Depends(get_db)):
    p = crud.get_page_by_slug(db, slug)
    if not p:
        raise HTTPException(404, "Страница не найдена")

    blocks = []
    for blk in crud.get_page_blocks(db, p.id):
        try:
            content = json.loads(blk.content_json or "{}")
        except Exception:
            content = {}
        blocks.append({
            "id": blk.id, "page_id": p.id,
            "kind": blk.kind, "content": content
        })

    return {
        "id": p.id, "slug": p.slug, "title": p.title,
        "is_home": p.is_home, "blocks": blocks
    }


# ==============================
# Admin UI page (защищено)
# ==============================
@app.get("/admin", response_class=HTMLResponse)
def admin_index(request: Request, user=Depends(require_user)):
    return templates.TemplateResponse("admin/index.html", {"request": request, "user": user})


# ==============================
# Admin API (всё защищено)
# ==============================
# ---- Reorder Buttons payload ----
class ButtonOrder(BaseModel):
    id: int
    order_index: int


class ButtonReorderPayload(BaseModel):
    items: List[ButtonOrder]

    # --- рядом с остальными pydantic-моделями:
class ButtonUpdate(BaseModel):
    title: Optional[str] = None
    target_slug: Optional[str] = None
    order_index: Optional[int] = None
    bg_color: Optional[str] = None
    text_color: Optional[str] = None
    icon_path: Optional[str] = None
    group_id: Optional[int] = None



# Buttons
@app.post("/admin/buttons", response_model=ButtonOut)
def create_btn(payload: ButtonCreate, db=Depends(get_db), user=Depends(require_user)):
    data = payload.model_dump()
    # авто-порядок, если не прислали
    if not data.get("order_index"):
        data["order_index"] = _next_button_order(db)
    # дефолт-цвета (на случай пустых форм)
    data.setdefault("bg_color", "#2563eb")
    data.setdefault("text_color", "#ffffff")
    return crud.create_button(db, data)


@app.put("/admin/buttons/{btn_id}", response_model=ButtonOut)
def update_btn(btn_id: int, payload: ButtonUpdate, db=Depends(get_db), user=Depends(require_user)):
    btn = db.query(models.Button).filter(models.Button.id == btn_id).first()
    if not btn:
        raise HTTPException(404, "Кнопка не найдена")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(btn, k, v)
    db.commit()
    db.refresh(btn)
    return btn



@app.post("/admin/buttons/reorder")
def reorder_buttons(payload: ButtonReorderPayload, db=Depends(get_db), user=Depends(require_user)):
    """
    Принимает: { "items": [ { "id": 1, "order_index": 1 }, ... ] }
    Обновляет порядок кнопок в одной транзакции.
    """
    ids = [it.id for it in payload.items]
    if not ids:
        return {"ok": True, "updated": 0}

    # Получим все затронутые кнопки
    buttons = db.query(models.Button).filter(models.Button.id.in_(ids)).all()
    by_id = {b.id: b for b in buttons}

    updated = 0
    for it in payload.items:
        btn = by_id.get(it.id)
        if not btn:
            continue
        btn.order_index = it.order_index
        updated += 1

    db.commit()
    return {"ok": True, "updated": updated}


@app.delete("/admin/buttons/{btn_id}")
def delete_btn(btn_id: int, db=Depends(get_db), user=Depends(require_user)):
    ok = crud.delete_button(db, btn_id)
    if not ok:
        raise HTTPException(404, "Кнопка не найдена")
    return {"ok": True}


# Pages
@app.get("/admin/pages", response_model=List[PageOut])
def list_pages_admin(db=Depends(get_db), user=Depends(require_user)):
    pages = crud.list_pages(db)
    out = []
    for p in pages:
        out.append({
            "id": p.id, "slug": p.slug, "title": p.title,
            "is_home": p.is_home, "blocks": []
        })
    return out


@app.post("/admin/pages", response_model=PageOut)
def create_page(payload: PageCreate, db=Depends(get_db), user=Depends(require_user)):
    page = crud.create_page(db, payload.model_dump())
    if page is None:
        raise HTTPException(409, "Page with this slug already exists")
    if page.is_home:
        _ensure_single_home(db, page.id)
    return {
        "id": page.id, "slug": page.slug, "title": page.title,
        "is_home": page.is_home, "blocks": []
    }


@app.put("/admin/pages/{slug}", response_model=PageOut)
def update_page(slug: str, payload: PageUpdate, db=Depends(get_db), user=Depends(require_user)):
    page = crud.update_page(db, slug, payload.model_dump())
    if not page:
        raise HTTPException(404, "Страница не найдена")
    if page.is_home:
        _ensure_single_home(db, page.id)

    blocks = []
    for blk in crud.get_page_blocks(db, page.id):
        blocks.append({
            "id": blk.id, "page_id": page.id, "kind": blk.kind,
            "content": json.loads(blk.content_json or "{}")
        })
    return {
        "id": page.id, "slug": page.slug, "title": page.title,
        "is_home": page.is_home, "blocks": blocks
    }



@app.delete("/admin/pages/{slug}")
def delete_page(slug: str, db=Depends(get_db), user=Depends(require_user)):
    p = crud.get_page_by_slug(db, slug)
    if not p:
        raise HTTPException(404, "Страница не найдена")
    db.delete(p)
    db.commit()
    return {"ok": True}


# Blocks
@app.post("/admin/blocks", response_model=BlockOut)
def create_block(payload: BlockCreate, db=Depends(get_db), user=Depends(require_user)):
    blk = crud.create_block(db, payload.page_id, payload.kind, payload.content)
    return {"id": blk.id, "page_id": blk.page_id, "kind": blk.kind, "content": payload.content}


@app.put("/admin/blocks/{block_id}", response_model=BlockOut)
def update_block(block_id: int, payload: BlockUpdate, db=Depends(get_db), user=Depends(require_user)):
    blk = crud.update_block(db, block_id, payload.kind, payload.content)
    if not blk:
        raise HTTPException(404, "Блок не найден")
    return {"id": blk.id, "page_id": blk.page_id, "kind": blk.kind, "content": payload.content}


@app.delete("/admin/blocks/{block_id}")
def delete_block(block_id: int, db=Depends(get_db), user=Depends(require_user)):
    ok = crud.delete_block(db, block_id)
    if not ok:
        raise HTTPException(404, "Блок не найден")
    return {"ok": True}


# Upload (только для админа)
@app.post("/upload")
def upload(file: UploadFile = File(...), user=Depends(require_user)):
    # Basic sanitization: keep only safe extension, randomize name
    import uuid
    name = file.filename or "file.bin"
    ext = os.path.splitext(name)[1].lower()
    if len(ext) > 10 or any(ch in ext for ch in ['/', '\\']):
        ext = ".bin"
    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(MEDIA_DIR, safe_name)
    # Optional lightweight size guard (~50 MB)
    max_bytes = 50 * 1024 * 1024
    total = 0
    with open(dest, "wb") as f:
        while True:
            chunk = file.file.read(512 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                f.close()
                try:
                    os.remove(dest)
                except Exception:
                    pass
                raise HTTPException(413, "File too large")
            f.write(chunk)
    return {"path": f"/media/{safe_name}"}


# ==============================
# Admin: Button Groups
# ==============================
@app.get("/admin/button-groups", response_model=List[ButtonGroupOut])
def list_button_groups(db=Depends(get_db), user=Depends(require_user)):
    return crud.get_button_groups(db)


@app.post("/admin/button-groups", response_model=ButtonGroupOut)
def create_button_group(payload: ButtonGroupCreate, db=Depends(get_db), user=Depends(require_user)):
    data = payload.model_dump()
    data.setdefault("bg_color", "#2563eb"); data.setdefault("text_color", "#ffffff")
    return crud.create_button_group(db, data)


@app.put("/admin/button-groups/{group_id}", response_model=ButtonGroupOut)
def update_button_group(group_id: int, payload: ButtonGroupUpdate, db=Depends(get_db), user=Depends(require_user)):
    grp = crud.update_button_group(db, group_id, payload.model_dump(exclude_unset=True))
    if not grp:
        raise HTTPException(404, "Группа не найдена")
    return grp


@app.delete("/admin/button-groups/{group_id}")
def delete_button_group(group_id: int, db=Depends(get_db), user=Depends(require_user)):
    ok = crud.delete_button_group(db, group_id)
    if not ok:
        raise HTTPException(404, "Группа не найдена")
    return {"ok": True}
# ==============================
# Settings & Config
# ==============================

@app.get("/config")
def get_config(db=Depends(get_db)):
    s = crud.get_settings(db)
    return {
        "org_name": s.org_name,
        "footer_qr_text": s.footer_qr_text,
        "footer_clock_format": s.footer_clock_format,
        "theme": s.theme,
        "exit_password_set": bool(s.exit_password_hash or ""),
        "show_weather": bool(getattr(s, 'show_weather', False)),
        "weather_city": getattr(s, 'weather_city', None),
    }


@app.put("/admin/settings")
def update_settings(payload: SettingsUpdate, db=Depends(get_db), user=Depends(require_user)):
    s = crud.get_settings(db)
    data = payload.model_dump(exclude_unset=True)
    org_name = data.get("org_name")
    if org_name is not None:
        s.org_name = org_name
    logo_path = data.get("logo_path")
    if logo_path is not None:
        if not s.theme:
            s.theme = models.Theme()
            db.add(s.theme); db.flush()
        s.theme.logo_path = logo_path
    kep = data.get("kiosk_exit_password")
    if kep:
        # захешируем как пароль пользователя
        try:
            from .crud import pwd_context
            s.exit_password_hash = pwd_context.hash(kep)
        except Exception:
            s.exit_password_hash = kep  # как fallback, но нежелательно
    # Weather toggles
    try:
        if "show_weather" in data:
            s.show_weather = bool(data.get("show_weather"))
        if "weather_city" in data:
            s.weather_city = (data.get("weather_city") or "").strip() or None
    except Exception:
        pass
    db.commit(); db.refresh(s)
    return {"ok": True}


class ExitCheck(BaseModel):
    password: str


@app.post("/kiosk/verify-exit")
def kiosk_verify_exit(payload: ExitCheck, db=Depends(get_db)):
    s = crud.get_settings(db)
    if not s or not s.exit_password_hash:
        # если пароль не задан — разрешаем выход
        return {"ok": True}
    try:
        from .crud import verify_password
        ok = verify_password(payload.password or "", s.exit_password_hash)
        return {"ok": bool(ok)}
    except Exception:
        return {"ok": False}


class KioskPwdSet(BaseModel):
    password: Optional[str] = None
    clear: Optional[bool] = False


@app.post("/admin/kiosk/exit-password")
def admin_set_exit_password(payload: KioskPwdSet, db=Depends(get_db), user=Depends(require_user)):
    s = crud.get_settings(db)
    if payload.clear:
        s.exit_password_hash = None
    elif (payload.password or "").strip():
        from .crud import pwd_context
        s.exit_password_hash = pwd_context.hash((payload.password or "").strip())
    else:
        # пустой запрос — игнор
        return {"ok": False, "reason": "empty"}
    db.commit(); db.refresh(s)
    return {"ok": True, "exit_password_set": bool(s.exit_password_hash)}


@app.get("/admin/kiosk/exit-password/status")
def admin_get_exit_password_status(db=Depends(get_db), user=Depends(require_user)):
    s = crud.get_settings(db)
    return {"exit_password_set": bool(s.exit_password_hash)}
