"""Helper script to build the packaged kiosk executable with PyInstaller."""

from __future__ import annotations

import os
import pathlib

import PyInstaller.__main__


ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "combined_launcher.py"


def _format_data_path(source: pathlib.Path, target: str) -> str:
    """Return an --add-data argument that works on any platform."""

    return f"{source}{os.pathsep}{target}"


def main() -> None:
    datas = [
        _format_data_path(ROOT / "backend" / "app" / "static", "backend/app/static"),
        _format_data_path(ROOT / "backend" / "app" / "templates", "backend/app/templates"),
        _format_data_path(ROOT / "backend" / "media", "backend/media"),
        _format_data_path(ROOT / "backend" / "app" / "kiosk.db", "backend/app/kiosk.db"),
    ]

    args = [
        str(ENTRYPOINT),
        "--name",
        "kiosk_app",
        "--onefile",
        "--noconfirm",
        "--clean",
    ]
    for data in datas:
        args.extend(["--add-data", data])

    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    main()
