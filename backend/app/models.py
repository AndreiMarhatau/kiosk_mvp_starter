from typing import Optional

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .db import Base

class ButtonGroup(Base):
    __tablename__ = "button_groups"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    bg_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    text_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

class Theme(Base):
    __tablename__ = "themes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), default="default")
    primary: Mapped[str] = mapped_column(String(20), default="#2563eb")
    bg: Mapped[str] = mapped_column(String(20), default="#f5f7fb")
    text: Mapped[str] = mapped_column(String(20), default="#0f1419")
    logo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

class Settings(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_name: Mapped[str] = mapped_column(String(120), default="Организация")
    footer_qr_text: Mapped[str] = mapped_column(String(255), default="")
    footer_clock_format: Mapped[str] = mapped_column(String(20), default="%H:%M")
    theme_id: Mapped[Optional[int]] = mapped_column(ForeignKey("themes.id"))
    theme: Mapped["Theme"] = relationship()
    # Пароль выхода из полноэкранного режима (bcrypt хэш)
    exit_password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Показ на киоске
    show_clock: Mapped[bool] = mapped_column(Boolean, default=True)
    show_date: Mapped[bool] = mapped_column(Boolean, default=True)
    show_weather: Mapped[bool] = mapped_column(Boolean, default=False)
    weather_city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

class Page(Base):
    __tablename__ = "pages"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    is_home: Mapped[bool] = mapped_column(Boolean, default=False)

    blocks: Mapped[list["Block"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )

class Block(Base):
    __tablename__ = "blocks"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # text|image|video|pdf
    content_json: Mapped[str] = mapped_column(Text, default="{}")

    page: Mapped["Page"] = relationship(back_populates="blocks")

class Button(Base):
    __tablename__ = "buttons"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120))
    target_slug: Mapped[str] = mapped_column(String(80))  # ссылаться на Page.slug
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    bg_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    text_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    icon_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("button_groups.id"), nullable=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="admin")
