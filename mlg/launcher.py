"""Odpalanie apek i folderów na Windowsie: kulki na orbitach HUD-a i narzędzie "otworz"."""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


class LaunchError(Exception):
    pass


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    kind: str  # "app" | "folder" | "tool"
    target: str  # ścieżka, URI (spotify:) albo nazwa programu (notepad)
    keys: tuple[str, ...] = field(default_factory=tuple)

    def verb(self) -> str:
        return f"Otwieram folder {self.name}" if self.kind == "folder" else f"Odpalam {self.name}"


def _home_folder(*names: str) -> str:
    """Zwykły folder użytkownika albo jego wersja w OneDrive (Windows lubi go tam przenosić)."""
    home = Path.home()
    for name in names:
        for base in (home, home / "OneDrive"):
            p = base / name
            if p.is_dir():
                return str(p)
    return str(home / names[0])


def default_items() -> list[list[Item]]:
    """Trzy orbity: apki najbliżej, potem foldery, na końcu narzędzia Windowsa."""
    return [
        [
            Item("spotify", "Spotify", "app", "spotify:", ("spotify", "muzyczk")),
            Item("discord", "Discord", "app", "discord://", ("discord", "dc")),
            Item("chrome", "Chrome", "app", "chrome", ("chrome", "przeglądark", "przegladark")),
            Item("steam", "Steam", "app", "steam://open/main", ("steam",)),
            Item("vscode", "VS Code", "app", "vscode://", ("vs code", "vscode", "visual studio code")),
        ],
        [
            Item("pulpit", "Pulpit", "folder", _home_folder("Desktop"), ("pulpit",)),
            Item("pobrane", "Pobrane", "folder", _home_folder("Downloads"), ("pobran",)),
            Item("dokumenty", "Dokumenty", "folder", _home_folder("Documents"), ("dokument",)),
            Item("zdjecia", "Zdjęcia", "folder", _home_folder("Pictures"), ("zdjęci", "zdjeci", "obraz")),
            Item("muzyka", "Muzyka", "folder", _home_folder("Music"), ("folder muzyk", "muzyka")),
            Item("filmy", "Filmy", "folder", _home_folder("Videos"), ("film", "wideo")),
        ],
        [
            Item("eksplorator", "Eksplorator", "tool", "explorer", ("eksplorator", "explorer", "plików", "plikow")),
            Item("notatnik", "Notatnik", "tool", "notepad", ("notatnik", "notepad")),
            Item("kalkulator", "Kalkulator", "tool", "calc", ("kalkulator",)),
            Item("ustawienia", "Ustawienia", "tool", "ms-settings:", ("ustawieni",)),
            Item("menedzer", "Menedżer zadań", "tool", "taskmgr", ("menedżer zadań", "menedzer zadan", "task manager")),
        ],
    ]


class Launcher:
    def __init__(self, orbits: list[list[Item]] | None = None):
        self.orbits = orbits if orbits is not None else default_items()
        self.items = {item.id: item for ring in self.orbits for item in ring}

    def find(self, query: str) -> Item | None:
        q = query.strip().lower()
        if not q:
            return None
        for item in self.items.values():
            if q == item.id or q == item.name.lower():
                return item
        for item in self.items.values():
            if any(k in q for k in item.keys) or item.name.lower() in q:
                return item
        return None

    def open(self, item: Item) -> str:
        if sys.platform != "win32":
            raise LaunchError("odpalanie programów działa tylko na Windowsie")
        if item.kind == "folder" and not Path(item.target).is_dir():
            raise LaunchError(f"nie ma folderu {item.target}")
        try:
            os.startfile(item.target)  # type: ignore[attr-defined]  # tylko Windows
        except OSError as e:
            raise LaunchError(f"nie udało się odpalić {item.name} (może nie jest zainstalowany?)") from e
        return f"{item.verb()}."
