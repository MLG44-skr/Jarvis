"""Narzędzia, których MLG może używać (tool calling w Ollamie)."""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from mlg.activity import Activity
from mlg.launcher import Launcher, LaunchError
from mlg.memory import Memory
from mlg.tools.calc import calculate
from mlg.tools.currency import get_rate
from mlg.tools.weather import get_weather

log = logging.getLogger("mlg.tools")


def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOL_SPECS = [
    _fn(
        "zapamietaj",
        "Zapisuje trwały fakt o szefie (imię, ulubione rzeczy, ludzie, praca, nawyki, preferencje). "
        "Używaj, gdy szef mówi coś o sobie, co warto pamiętać na przyszłość.",
        {"fakt": {"type": "string", "description": "Krótki fakt w 3. osobie, np. 'Szef ma psa o imieniu Burek'"}},
        ["fakt"],
    ),
    _fn(
        "dodaj_przypomnienie",
        "Ustawia przypomnienie. Podaj 'kiedy' (dokładna data i godzina) ALBO 'za_minut' (za ile minut od teraz).",
        {
            "tresc": {"type": "string", "description": "O czym przypomnieć"},
            "kiedy": {"type": "string", "description": "Data i godzina w formacie 'RRRR-MM-DD GG:MM' albo sama godzina 'GG:MM'"},
            "za_minut": {"type": "integer", "description": "Za ile minut od teraz"},
        },
        ["tresc"],
    ),
    _fn("pokaz_przypomnienia", "Pokazuje zaplanowane przypomnienia.", {}, []),
    _fn(
        "dodaj_do_listy",
        "Dodaje pozycję do listy (np. zakupy, todo, filmy).",
        {
            "lista": {"type": "string", "description": "Nazwa listy, np. 'zakupy'"},
            "pozycja": {"type": "string", "description": "Co dodać. Kilka rzeczy oddziel przecinkami."},
        },
        ["lista", "pozycja"],
    ),
    _fn(
        "pokaz_liste",
        "Pokazuje zawartość listy. Bez nazwy pokazuje, jakie listy istnieją.",
        {"lista": {"type": "string", "description": "Nazwa listy, np. 'zakupy'"}},
        [],
    ),
    _fn(
        "usun_z_listy",
        "Usuwa pozycję z listy. Pozycja '*' czyści całą listę.",
        {
            "lista": {"type": "string", "description": "Nazwa listy"},
            "pozycja": {"type": "string", "description": "Co usunąć albo '*' żeby wyczyścić listę"},
        },
        ["lista", "pozycja"],
    ),
    _fn(
        "pogoda",
        "Sprawdza aktualną pogodę i prognozę na dziś i jutro.",
        {"miasto": {"type": "string", "description": "Nazwa miasta. Puste = domyślne miasto szefa."}},
        [],
    ),
    _fn(
        "kurs_waluty",
        "Sprawdza aktualny kurs waluty w złotówkach (NBP).",
        {"kod": {"type": "string", "description": "Kod waluty, np. EUR, USD, GBP, CHF"}},
        ["kod"],
    ),
    _fn(
        "otworz",
        "Odpala program albo otwiera folder na komputerze szefa (np. Spotify, Discord, Chrome, Steam, VS Code, "
        "Pobrane, Dokumenty, Pulpit, Notatnik, Kalkulator, Ustawienia).",
        {"co": {"type": "string", "description": "Nazwa programu albo folderu, np. 'Spotify' albo 'Pobrane'"}},
        ["co"],
    ),
    _fn(
        "oblicz",
        "Liczy wyrażenie matematyczne. Zawsze używaj do obliczeń zamiast liczyć w głowie.",
        {"wyrazenie": {"type": "string", "description": "Np. '(120*3)/4' albo '2^10'"}},
        ["wyrazenie"],
    ),
]


def parse_when(kiedy: str | None, za_minut: Any, now: datetime) -> datetime:
    if za_minut not in (None, ""):
        minutes = int(float(za_minut))
        if minutes <= 0:
            raise ValueError("liczba minut musi być większa od zera")
        return now + timedelta(minutes=minutes)
    if not kiedy:
        raise ValueError("brak terminu: podaj 'kiedy' albo 'za_minut'")
    kiedy = kiedy.strip().replace("T", " ")
    if len(kiedy) <= 5:  # sama godzina, np. "9.30"
        kiedy = kiedy.replace(".", ":")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(kiedy, fmt)
        except ValueError:
            pass
    try:
        t = datetime.strptime(kiedy, "%H:%M").time()
    except ValueError:
        raise ValueError(f"nie rozumiem terminu '{kiedy}', użyj 'RRRR-MM-DD GG:MM'") from None
    when = datetime.combine(now.date(), t)
    return when if when > now else when + timedelta(days=1)


class Toolbox:
    """Wykonuje narzędzia w imieniu konkretnego szefa (user_id) w konkretnym czacie."""

    def __init__(
        self, memory: Memory, http: httpx.AsyncClient, default_city: str, user_id: int, chat_id: int,
        launcher: Launcher | None = None, activity: Activity | None = None,
    ):
        self.memory = memory
        self.http = http
        self.default_city = default_city
        self.user_id = user_id
        self.chat_id = chat_id
        self.launcher = launcher or Launcher()
        self.activity = activity
        self.actions: list[str] = []  # nazwy użytych narzędzi (do logów i testów)

    async def run(self, name: str, args: dict[str, Any] | None) -> str:
        args = args or {}
        handler = getattr(self, f"_t_{name}", None)
        if handler is None:
            return f"Błąd: nie ma narzędzia '{name}'."
        try:
            result = await handler(**{k: v for k, v in args.items() if v is not None})
        except TypeError as e:
            return f"Błąd: złe parametry dla '{name}' ({e})."
        except (ValueError, LaunchError) as e:
            return f"Błąd: {e}."
        except httpx.HTTPError as e:
            log.warning("Narzędzie %s: błąd sieci %s", name, e)
            return "Błąd: brak połączenia z serwisem. Spróbuj później."
        self.actions.append(name)
        if self.activity and name != "otworz":
            self.activity.tool(name)
        return result

    async def _t_zapamietaj(self, fakt: str) -> str:
        fact = self.memory.add_fact(self.user_id, fakt)
        return f"Zapamiętane (#{fact.id}): {fact.text}"

    async def _t_dodaj_przypomnienie(self, tresc: str, kiedy: str | None = None, za_minut: Any = None) -> str:
        now = datetime.now()
        when = parse_when(kiedy, za_minut, now)
        if when <= now:
            raise ValueError("ten termin już minął")
        rid = self.memory.add_reminder(self.user_id, self.chat_id, when, tresc)
        return f"Przypomnienie #{rid} ustawione na {when:%d.%m.%Y %H:%M}: {tresc}"

    async def _t_pokaz_przypomnienia(self) -> str:
        items = self.memory.pending_reminders(self.user_id)
        if not items:
            return "Brak zaplanowanych przypomnień."
        return "\n".join(f"#{r.id} {r.due_at:%d.%m %H:%M}: {r.text}" for r in items)

    async def _t_dodaj_do_listy(self, lista: str, pozycja: str) -> str:
        items = [p.strip() for p in pozycja.split(",") if p.strip()]
        for item in items:
            self.memory.add_list_item(self.user_id, lista, item)
        return f"Dodano do listy '{lista}': {', '.join(items)}. Teraz na liście: {', '.join(self.memory.list_items(self.user_id, lista))}"

    async def _t_pokaz_liste(self, lista: str = "") -> str:
        if not lista.strip():
            names = self.memory.list_names(self.user_id)
            return "Listy: " + ", ".join(names) if names else "Nie ma jeszcze żadnych list."
        items = self.memory.list_items(self.user_id, lista)
        return f"Lista '{lista}': " + ", ".join(items) if items else f"Lista '{lista}' jest pusta."

    async def _t_usun_z_listy(self, lista: str, pozycja: str) -> str:
        if pozycja.strip() == "*":
            n = self.memory.clear_list(self.user_id, lista)
            return f"Wyczyszczono listę '{lista}' ({n} pozycji)."
        n = self.memory.remove_list_item(self.user_id, lista, pozycja)
        return f"Usunięto z listy '{lista}': {pozycja}." if n else f"Nie znalazłem '{pozycja}' na liście '{lista}'."

    async def _t_pogoda(self, miasto: str = "") -> str:
        city = miasto.strip() or self.default_city
        if not city:
            return "Nie znam miasta. Zapytaj szefa, dla jakiego miasta sprawdzić (może ustawić DEFAULT_CITY w .env)."
        return await get_weather(self.http, city)

    async def _t_kurs_waluty(self, kod: str) -> str:
        return await get_rate(self.http, kod)

    async def _t_otworz(self, co: str) -> str:
        item = self.launcher.find(co)
        if item is None:
            known = ", ".join(i.name for i in self.launcher.items.values())
            return f"Nie znam '{co}'. Umiem odpalić: {known}."
        if self.activity:
            self.activity.highlight(item.id)
        result = self.launcher.open(item)
        if self.activity:
            self.activity.log(item.verb())
        return result

    async def _t_oblicz(self, wyrazenie: str) -> str:
        return calculate(wyrazenie)
