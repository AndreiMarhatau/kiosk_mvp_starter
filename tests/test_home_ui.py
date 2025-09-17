from __future__ import annotations

from typing import List

from tests.qt_stubs import install_qt_stubs

install_qt_stubs()

from kiosk_app.ui.home import DropList, GroupTile  # noqa: E402


THEME = {
    "primary": "#0f172a",
    "tile_h": 120,
}


def _items(*slugs: str) -> List[dict]:
    return [
        {"title": slug.title(), "target_slug": slug}
        for slug in slugs
    ]


def test_droplist_rebuilds_buttons_when_items_change() -> None:
    droplist = DropList(THEME, _items("alpha"), on_pick=None)

    assert droplist.button_count() == 1

    droplist.set_items(_items("alpha", "beta"))
    assert droplist.button_count() == 2

    droplist.set_items([])
    assert droplist.button_count() == 0


def test_group_tile_reuses_existing_popup() -> None:
    picked: List[str] = []
    tile = GroupTile("Group", _items("alpha"), THEME, on_pick=picked.append)

    popup_first = tile._ensure_popup()  # type: ignore[attr-defined]
    assert popup_first.button_count() == 1

    tile.items = _items("alpha", "beta")
    popup_second = tile._ensure_popup()  # type: ignore[attr-defined]

    assert popup_first is popup_second
    assert popup_second.button_count() == 2

    popup_second.show()
    popup_second._buttons[1].click()  # type: ignore[attr-defined]

    assert picked == ["beta"]
    assert popup_second.isVisible() is False


def test_droplist_hides_even_without_callback() -> None:
    droplist = DropList(THEME, _items("alpha"), on_pick=None)
    droplist.show()

    droplist._buttons[0].click()  # type: ignore[attr-defined]

    assert droplist.isVisible() is False
