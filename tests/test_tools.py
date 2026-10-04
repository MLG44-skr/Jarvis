from datetime import datetime

import httpx
import pytest

from conftest import run
from mlg.tools import Toolbox, parse_when
from mlg.tools.calc import calculate

NOW = datetime(2026, 10, 4, 12, 0)


def test_parse_when():
    assert parse_when(None, 30, NOW) == datetime(2026, 10, 4, 12, 30)
    assert parse_when("2026-10-05 09:00", None, NOW) == datetime(2026, 10, 5, 9, 0)
    assert parse_when("2026-10-05T09:00", None, NOW) == datetime(2026, 10, 5, 9, 0)
    assert parse_when("15:00", None, NOW) == datetime(2026, 10, 4, 15, 0)
    assert parse_when("9.30", None, NOW) == datetime(2026, 10, 5, 9, 30)  # już minęło dziś -> jutro
    with pytest.raises(ValueError):
        parse_when("kiedyś", None, NOW)
    with pytest.raises(ValueError):
        parse_when(None, None, NOW)
    with pytest.raises(ValueError):
        parse_when(None, 0, NOW)


def test_calc():
    assert calculate("(120*3)/4") == "(120*3)/4 = 90"
    assert calculate("2^10") == "2^10 = 1024"
    assert calculate("0,1+0,2") == "0,1+0,2 = 0.3"
    assert "dzielenie przez zero" in calculate("1/0")
    assert calculate("__import__('os')").startswith("Błąd")
    assert calculate("9**9999").startswith("Błąd")


def fake_http() -> httpx.AsyncClient:
    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if "geocoding-api.open-meteo.com" in url:
            if req.url.params["name"] == "Nibylandia":
                return httpx.Response(200, json={"generationtime_ms": 0.1})
            return httpx.Response(200, json={"results": [{"name": "Kraków", "latitude": 50.06, "longitude": 19.94}]})
        if "api.open-meteo.com" in url:
            return httpx.Response(200, json={
                "current": {"temperature_2m": 14.2, "apparent_temperature": 12.9, "weather_code": 2, "wind_speed_10m": 9.4},
                "daily": {"weather_code": [2, 61], "temperature_2m_max": [16.1, 13.0],
                          "temperature_2m_min": [7.3, 8.0], "precipitation_probability_max": [10, 80]},
            })
        if "api.nbp.pl" in url:
            if "/xyz/" in url:
                return httpx.Response(404, text="404 NotFound")
            return httpx.Response(200, json={"table": "A", "currency": "euro", "code": "EUR",
                                             "rates": [{"no": "1/A/NBP/2026", "effectiveDate": "2026-10-02", "mid": 4.2731}]})
        return httpx.Response(500)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def toolbox(memory, city="") -> Toolbox:
    return Toolbox(memory, fake_http(), city, user_id=1, chat_id=100)


def test_weather(memory):
    tb = toolbox(memory, city="Kraków")
    out = run(tb.run("pogoda", {}))
    assert "Kraków: teraz 14.2°C" in out and "częściowe zachmurzenie" in out
    assert "Jutro: 8.0–13.0°C, lekki deszcz, szansa opadów 80%" in out
    assert "Nie znalazłem" in run(tb.run("pogoda", {"miasto": "Nibylandia"}))
    assert "Nie znam miasta" in run(toolbox(memory).run("pogoda", {}))


def test_currency(memory):
    tb = toolbox(memory)
    assert run(tb.run("kurs_waluty", {"kod": "eur"})) == "1 EUR = 4.2731 PLN (kurs średni NBP z 2026-10-02)."
    assert "nie podaje kursu" in run(tb.run("kurs_waluty", {"kod": "XYZ"}))
    assert "to nie jest kod waluty" in run(tb.run("kurs_waluty", {"kod": "euro"}))


def test_lists_and_memory_tools(memory):
    tb = toolbox(memory)
    out = run(tb.run("dodaj_do_listy", {"lista": "zakupy", "pozycja": "mleko, chleb"}))
    assert "mleko, chleb" in out
    assert run(tb.run("pokaz_liste", {"lista": "zakupy"})) == "Lista 'zakupy': mleko, chleb"
    assert run(tb.run("pokaz_liste", {})) == "Listy: zakupy"
    assert "Usunięto" in run(tb.run("usun_z_listy", {"lista": "zakupy", "pozycja": "mleko"}))
    assert "Wyczyszczono" in run(tb.run("usun_z_listy", {"lista": "zakupy", "pozycja": "*"}))
    assert "Zapamiętane" in run(tb.run("zapamietaj", {"fakt": "Szef gra w CS2"}))
    assert [f.text for f in memory.facts(1)] == ["Szef gra w CS2"]
    assert tb.actions == ["dodaj_do_listy", "pokaz_liste", "pokaz_liste", "usun_z_listy", "usun_z_listy", "zapamietaj"]


def test_reminder_tool(memory):
    tb = toolbox(memory)
    out = run(tb.run("dodaj_przypomnienie", {"tresc": "trening", "za_minut": "45"}))
    assert out.startswith("Przypomnienie #1 ustawione")
    assert memory.pending_reminders(1)[0].chat_id == 100
    assert "trening" in run(tb.run("pokaz_przypomnienia", {}))
    assert run(tb.run("dodaj_przypomnienie", {"tresc": "x", "kiedy": "2020-01-01 10:00"})) == "Błąd: ten termin już minął."


def test_bad_tool_calls(memory):
    tb = toolbox(memory)
    assert "nie ma narzędzia" in run(tb.run("hakuj_nasa", {}))
    assert "złe parametry" in run(tb.run("oblicz", {"cos": "1+1"}))
    assert tb.actions == []
