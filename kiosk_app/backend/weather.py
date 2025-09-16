from __future__ import annotations

from typing import Optional, Tuple

import requests


def fetch_weather(city: str) -> Tuple[Optional[str], Optional[float], Optional[int]]:
    city = (city or "").strip()
    if not city:
        return None, None, None
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "ru", "format": "json"},
            timeout=6,
        ).json()
        results = (geo or {}).get("results") or []
        if not results:
            return None, None, None
        location = results[0]
        lat = location.get("latitude")
        lon = location.get("longitude")
        if lat is None or lon is None:
            return None, None, None
        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": True, "timezone": "auto"},
            timeout=6,
        ).json()
        current = (forecast or {}).get("current_weather") or {}
        temp = current.get("temperature")
        code = current.get("weathercode")
        if temp is None:
            current = (forecast or {}).get("current") or {}
            temp = current.get("temperature_2m") if isinstance(current, dict) else None
            code = current.get("weather_code") if isinstance(current, dict) else code
        display_city = location.get("name") or city
        if isinstance(temp, (int, float)):
            try:
                temp = float(temp)
            except Exception:
                temp = None
        else:
            temp = None
        return display_city, temp, code if isinstance(code, (int, float)) else None
    except Exception:
        return None, None, None
