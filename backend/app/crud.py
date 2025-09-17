# backend/app/crud.py
import json
from sqlalchemy.orm import Session
from . import models
from passlib.context import CryptContext
from .models import User
from sqlalchemy import text


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, password: str, role: str = "admin") -> User | None:
    """Create a new user. Returns None if username already exists."""
    existing = get_user_by_username(db, username)
    if existing:
        return None
    u = User(username=username, password_hash=pwd_context.hash(password), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def ensure_admin_user(db: Session, username="admin", password="admin"):
    u = get_user_by_username(db, username)
    if u: return u
    u = User(username=username, password_hash=pwd_context.hash(password), role="admin")
    db.add(u); db.commit(); db.refresh(u)
    return u

def verify_password(plain: str, password_hash: str) -> bool:
    return pwd_context.verify(plain, password_hash)

def get_settings(db: Session) -> models.Settings:
    s = db.query(models.Settings).first()
    if s: return s
    theme = models.Theme()
    db.add(theme); db.flush()
    s = models.Settings(theme_id=theme.id)
    db.add(s); db.commit(); db.refresh(s)
    return s

def get_home_buttons(db: Session):
    # top-level buttons only (exclude grouped)
    return (
        db.query(models.Button)
        .filter(models.Button.group_id == None)  # noqa: E711
        .order_by(models.Button.order_index)
        .all()
    )

def get_button_groups(db: Session):
    return db.query(models.ButtonGroup).order_by(models.ButtonGroup.order_index).all()

def create_button_group(db: Session, data: dict) -> models.ButtonGroup:
    grp = models.ButtonGroup(**data)
    db.add(grp); db.commit(); db.refresh(grp)
    return grp

def update_button_group(db: Session, group_id: int, data: dict) -> models.ButtonGroup | None:
    grp = db.get(models.ButtonGroup, group_id)
    if not grp: return None
    for k, v in data.items():
        if v is not None:
            setattr(grp, k, v)
    db.commit(); db.refresh(grp)
    return grp

def delete_button_group(db: Session, group_id: int) -> bool:
    grp = db.get(models.ButtonGroup, group_id)
    if not grp: return False
    # detach buttons from group
    db.query(models.Button).filter(models.Button.group_id == group_id).update({models.Button.group_id: None})
    db.delete(grp); db.commit()
    return True

def get_menu_tree(db: Session):
    groups = get_button_groups(db)
    out = []
    # map items by group
    for g in groups:
        items = db.query(models.Button).filter(models.Button.group_id == g.id).order_by(models.Button.order_index).all()
        out.append({
            "kind": "group",
            "id": g.id,
            "title": g.title,
            "order_index": g.order_index,
            "bg_color": g.bg_color,
            "text_color": g.text_color,
            "items": [
                {
                    "id": b.id, "title": b.title, "target_slug": b.target_slug,
                    "order_index": b.order_index, "bg_color": b.bg_color,
                    "text_color": b.text_color, "icon_path": b.icon_path
                } for b in items
            ]
        })
    # add standalone buttons (no group)
    top = db.query(models.Button).filter(models.Button.group_id == None).order_by(models.Button.order_index).all()
    out.extend([
        {
            "kind": "button",
            "id": b.id, "title": b.title, "target_slug": b.target_slug,
            "order_index": b.order_index, "bg_color": b.bg_color,
            "text_color": b.text_color, "icon_path": b.icon_path
        } for b in top
    ])
    # sort by order_index across top-level
    out.sort(key=lambda x: x.get("order_index") or 0)
    return out

def ensure_button_groups_schema(db: Session):
    # create table if not exists
    db.execute(text(
        """
        CREATE TABLE IF NOT EXISTS button_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(120) NOT NULL,
            order_index INTEGER DEFAULT 0,
            bg_color VARCHAR(20),
            text_color VARCHAR(20)
        )
        """
    ))
    # add group_id column if not exists
    cols = db.execute(text("PRAGMA table_info(buttons)")).fetchall()
    if not any(c[1] == 'group_id' for c in cols):
        db.execute(text("ALTER TABLE buttons ADD COLUMN group_id INTEGER"))
    db.commit()

def ensure_settings_columns(db: Session):
    """Проверяем и добавляем недостающие колонки в settings."""
    cols = db.execute(text("PRAGMA table_info(settings)")).fetchall()
    names = {c[1] for c in cols}
    if 'exit_password_hash' not in names:
        db.execute(text("ALTER TABLE settings ADD COLUMN exit_password_hash VARCHAR(255)"))
        db.commit()

def ensure_settings_columns(db: Session):
    """Ensure newly added Settings columns exist (for SQLite dev DBs)."""
    cols = db.execute(text("PRAGMA table_info(settings)")).fetchall()
    names = {c[1] for c in cols}
    # Kiosk exit password hash
    if 'exit_password_hash' not in names:
        db.execute(text("ALTER TABLE settings ADD COLUMN exit_password_hash VARCHAR(255)"))
        db.commit()
    # Footer visibility toggles and weather settings
    if 'show_clock' not in names:
        db.execute(text("ALTER TABLE settings ADD COLUMN show_clock BOOLEAN DEFAULT 1"))
        db.commit()
    if 'show_date' not in names:
        db.execute(text("ALTER TABLE settings ADD COLUMN show_date BOOLEAN DEFAULT 1"))
        db.commit()
    if 'show_weather' not in names:
        db.execute(text("ALTER TABLE settings ADD COLUMN show_weather BOOLEAN DEFAULT 0"))
        db.commit()
    if 'weather_city' not in names:
        db.execute(text("ALTER TABLE settings ADD COLUMN weather_city VARCHAR(120)"))
        db.commit()
    if 'screensaver_path' not in names:
        db.execute(text("ALTER TABLE settings ADD COLUMN screensaver_path VARCHAR(255)"))
        db.commit()
    if 'screensaver_timeout' not in names:
        db.execute(text("ALTER TABLE settings ADD COLUMN screensaver_timeout INTEGER DEFAULT 0"))
        db.commit()


def ensure_theme_columns(db: Session):
    cols = db.execute(text("PRAGMA table_info(themes)")).fetchall()
    names = {c[1] for c in cols}
    if 'bg_image_path' not in names:
        db.execute(text("ALTER TABLE themes ADD COLUMN bg_image_path VARCHAR(255)"))
        db.commit()

def list_pages(db: Session):
    return db.query(models.Page).all()

def get_page_by_slug(db: Session, slug: str) -> models.Page | None:
    return db.query(models.Page).filter(models.Page.slug == slug).first()

def get_page_blocks(db: Session, page_id: int):
    return (
        db.query(models.Block)
        .filter(models.Block.page_id == page_id)
        .order_by(models.Block.order_index, models.Block.id)
        .all()
    )

def create_button(db: Session, data: dict) -> models.Button:
    btn = models.Button(**data)
    db.add(btn); db.commit(); db.refresh(btn)
    return btn

def delete_button(db: Session, btn_id: int) -> bool:
    btn = db.get(models.Button, btn_id)
    if not btn: return False
    db.delete(btn); db.commit()
    return True

# ---- Pages ----
def create_page(db: Session, data: dict) -> models.Page:
    page = models.Page(**data)
    db.add(page); db.commit(); db.refresh(page)
    return page

def update_page(db: Session, slug: str, data: dict) -> models.Page | None:
    page = get_page_by_slug(db, slug)
    if not page: return None
    for k, v in data.items():
        if v is not None:
            setattr(page, k, v)
    db.commit(); db.refresh(page)
    return page

# ---- Blocks ----
def create_block(db: Session, page_id: int, kind: str, content: dict) -> models.Block:
    last = (
        db.query(models.Block.order_index)
        .filter(models.Block.page_id == page_id)
        .order_by(models.Block.order_index.desc())
        .first()
    )
    next_ord = (last[0] + 1) if last and last[0] is not None else 1
    blk = models.Block(page_id=page_id, kind=kind, content_json=json.dumps(content, ensure_ascii=False), order_index=next_ord)
    db.add(blk); db.commit(); db.refresh(blk)
    return blk

def update_block(db: Session, block_id: int, kind: str, content: dict) -> models.Block | None:
    blk = db.get(models.Block, block_id)
    if not blk: return None
    blk.kind = kind
    blk.content_json = json.dumps(content, ensure_ascii=False)
    db.commit(); db.refresh(blk)
    return blk

def delete_block(db: Session, block_id: int) -> bool:
    blk = db.get(models.Block, block_id)
    if not blk: return False
    db.delete(blk); db.commit()
    return True

def upsert_sample_content(db: Session):
    # демо-страницы
    if not get_page_by_slug(db, "about"):
        db.add(models.Page(slug="about", title="О компании"))
    if not get_page_by_slug(db, "services"):
        db.add(models.Page(slug="services", title="Услуги"))
    if not get_page_by_slug(db, "contacts"):
        db.add(models.Page(slug="contacts", title="Контакты"))
    db.commit()
    # кнопки
    if db.query(models.Button).count() == 0:
        db.add_all([
            models.Button(title="О компании", target_slug="about", order_index=0),
            models.Button(title="Услуги", target_slug="services", order_index=1),
            models.Button(title="Контакты", target_slug="contacts", order_index=2),
        ])
        db.commit()
    # базовый текстовый блок для about (один раз)
    about = get_page_by_slug(db, "about")
    if about and not get_page_blocks(db, about.id):
        create_block(db, about.id, "text", {"html": "<h2>О нас</h2><p>Добро пожаловать!</p>"})

def ensure_block_order_column(db: Session):
    """Ensure blocks.order_index column exists (SQLite dev DBs) and backfill values.
    Adds the column if missing and assigns sequential order per page based on id.
    """
    cols = db.execute(text("PRAGMA table_info(blocks)")).fetchall()
    names = {c[1] for c in cols}
    if 'order_index' not in names:
        db.execute(text("ALTER TABLE blocks ADD COLUMN order_index INTEGER DEFAULT 0"))
        db.commit()
        rows = db.execute(text("SELECT id, page_id FROM blocks ORDER BY page_id, id")).fetchall()
        cur_page = None
        idx = 0
        for rid, pid in rows:
            if pid != cur_page:
                cur_page = pid
                idx = 1
            db.execute(text("UPDATE blocks SET order_index=:oi WHERE id=:id"), {"oi": idx, "id": rid})
            idx += 1
        db.commit()
