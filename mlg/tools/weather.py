"""Pogoda z Open-Meteo (darmowe, bez klucza)."""

import httpx

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_CODES = {
    0: "bezchmurnie",
    1: "przeważnie słonecznie",
    2: "częściowe zachmurzenie",
    3: "pochmurno",
    45: "mgła",
    48: "mgła z szadzią",
    51: "lekka mżawka",
    53: "mżawka",
    55: "gęsta mżawka",
    56: "marznąca mżawka",
    57: "marznąca mżawka",
    61: "lekki deszcz",
    63: "deszcz",
    65: "ulewny deszcz",
    66: "marznący deszcz",
    67: "marznący deszcz",
    71: "lekki śnieg",
    73: "śnieg",
    75: "intensywny śnieg",
    77: "ziarnisty śnieg",
    80: "przelotne opady",
    81: "przelotny deszcz",
    82: "gwałtowne ulewy",
    85: "przelotny śnieg",
    86: "intensywne opady śniegu",
    95: "burza",
    96: "burza z gradem",
    99: "silna burza z gradem",
}


def describe(code: int | None) -> str:
    return _CODES.get(code, "brak opisu") if code is not None else "brak opisu"


async def get_weather(http: httpx.AsyncClient, city: str) -> str:
    geo = await http.get(GEO_URL, params={"name": city, "count": 1, "language": "pl"})
    geo.raise_for_status()
    results = geo.json().get("results") or []
    if not results:
        return f"Nie znalazłem miasta '{city}'."
    place = results[0]

    fc = await http.get(
        FORECAST_URL,
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 2,
        },
    )
    fc.raise_for_status()
    data = fc.json()
    cur = data.get("current", {})
    daily = data.get("daily", {})

    lines = [
        f"{place.get('name', city)}: teraz {cur.get('temperature_2m')}°C "
        f"(odczuwalna {cur.get('apparent_temperature')}°C), {describe(cur.get('weather_code'))}, "
        f"wiatr {cur.get('wind_speed_10m')} km/h."
    ]
    for i, label in enumerate(["Dziś", "Jutro"]):
        try:
            lines.append(
                f"{label}: {daily['temperature_2m_min'][i]}–{daily['temperature_2m_max'][i]}°C, "
                f"{describe(daily['weather_code'][i])}, szansa opadów {daily['precipitation_probability_max'][i]}%."
            )
        except (KeyError, IndexError):
            break
    return "\n".join(lines)
