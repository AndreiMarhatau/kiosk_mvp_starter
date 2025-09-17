# backend/app/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Dict

class ThemeOut(BaseModel):
    id: int
    name: str
    primary: str
    bg: str
    text: str
    logo_path: Optional[str] = None
    bg_image_path: Optional[str] = None
    class Config: from_attributes = True

class ScreensaverOut(BaseModel):
    path: Optional[str] = None
    timeout: int = 0

class ConfigOut(BaseModel):
    org_name: str
    footer_qr_text: str
    footer_clock_format: str
    theme: ThemeOut
    screensaver: ScreensaverOut | None = None
    show_weather: bool | None = None
    weather_city: Optional[str] = None

class SettingsUpdate(BaseModel):
    org_name: Optional[str] = None
    logo_path: Optional[str] = None
    kiosk_exit_password: Optional[str] = None  # plaintext from admin UI; backend will hash
    show_weather: Optional[bool] = None
    weather_city: Optional[str] = None

class ThemeUpdate(BaseModel):
    primary: Optional[str] = None
    bg: Optional[str] = None
    text: Optional[str] = None
    bg_image_path: Optional[str] = None

class ScreensaverUpdate(BaseModel):
    path: Optional[str] = None
    timeout: Optional[int] = None

# -------- Buttons --------
class ButtonBase(BaseModel):
    title: str
    target_slug: str
    order_index: int = 0
    bg_color: Optional[str] = None
    text_color: Optional[str] = None
    icon_path: Optional[str] = None
    group_id: Optional[int] = None

class ButtonCreate(ButtonBase): pass
class ButtonOut(ButtonBase):
    id: int
    class Config: from_attributes = True

# -------- Blocks --------
class BlockBase(BaseModel):
    kind: str                          # text | image | video | pdf
    content: Dict                      # {html: "..."} или {path: "...", ...}

class BlockCreate(BlockBase):
    page_id: int

class BlockUpdate(BlockBase): pass

class BlockOut(BlockBase):
    id: int
    page_id: int
    class Config: from_attributes = True

# -------- Pages --------
class PageBase(BaseModel):
    slug: str
    title: str
    is_home: bool = False

class PageCreate(PageBase): pass

class PageUpdate(BaseModel):
    title: Optional[str] = None
    is_home: Optional[bool] = None

class PageOut(PageBase):
    id: int
    blocks: List[BlockOut] = []
    class Config: from_attributes = True

# -------- Users --------
class UserCreate(BaseModel):
    username: str
    password: str
    role: Optional[str] = "admin"

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    class Config: from_attributes = True

# -------- Button Groups --------
class ButtonGroupBase(BaseModel):
    title: str
    order_index: int = 0
    bg_color: Optional[str] = None
    text_color: Optional[str] = None

class ButtonGroupCreate(ButtonGroupBase):
    pass

class ButtonGroupUpdate(BaseModel):
    title: Optional[str] = None
    order_index: Optional[int] = None
    bg_color: Optional[str] = None
    text_color: Optional[str] = None

class ButtonGroupOut(ButtonGroupBase):
    id: int
    class Config: from_attributes = True
