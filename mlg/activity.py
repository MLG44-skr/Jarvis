"""Co MLG właśnie robi: log akcji i podświetlona kulka dla HUD-a."""

import time
from collections import deque
from datetime import datetime

TOOL_LABELS = {
    "zapamietaj": "Zapisuję w pamięci",
    "dodaj_przypomnienie": "Ustawiam przypomnienie",
    "pokaz_przypomnienia": "Sprawdzam przypomnienia",
    "dodaj_do_listy": "Dopisuję do listy",
    "pokaz_liste": "Sprawdzam listę",
    "usun_z_listy": "Usuwam z listy",
    "pogoda": "Sprawdzam pogodę",
    "kurs_waluty": "Sprawdzam kurs waluty",
    "oblicz": "Liczę",
    "otworz": "Odpalam",
}

ACTIVE_SECONDS = 4.5


class Activity:
    def __init__(self, size: int = 30):
        self.events: deque[dict] = deque(maxlen=size)
        self.busy = 0
        self.active_item: str | None = None
        self._active_until = 0.0

    def log(self, text: str) -> None:
        self.events.appendleft({"at": datetime.now().strftime("%H:%M"), "text": text})

    def tool(self, name: str, detail: str = "") -> None:
        label = TOOL_LABELS.get(name, name)
        self.log(f"{label} {detail}".strip())

    def highlight(self, item_id: str) -> None:
        self.active_item = item_id
        self._active_until = time.monotonic() + ACTIVE_SECONDS

    def current_item(self) -> str | None:
        if self.active_item and time.monotonic() < self._active_until:
            return self.active_item
        return None
