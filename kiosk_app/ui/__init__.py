"""UI components for the kiosk application."""

from .header import Header
from .footer import Footer
from .home import HomePage
from .page import PageView
from .admin import AdminView
from .dialogs import ExitPwdDialog, install_password_dialog_patch

__all__ = [
    "Header",
    "Footer",
    "HomePage",
    "PageView",
    "AdminView",
    "ExitPwdDialog",
    "install_password_dialog_patch",
]
