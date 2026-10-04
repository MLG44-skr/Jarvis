# 🤖 Plan Jarvis

Osobisty asystent AI w stylu Jarvisa z Iron Mana — połączony z Telegramem, działający na Windowsie, z minimalnym kosztem.

---

## 🎯 Założenia budżetowe

| Element | Rozwiązanie | Koszt |
|---|---|---|
| 🧠 Mózg | Claude **Haiku 4.5** ($1 / $5 za 1M tokenów) — w razie potrzeby przełączany na Sonnet/Opus jedną linijką | ~10–30 zł/mies. |
| 🎙️ Słuch | Whisper lokalnie (`faster-whisper`) | 0 zł |
| 🔊 Głos | Piper TTS lokalnie | 0 zł |
| 💬 Interfejs | Telegram Bot API | 0 zł |
| 🖥️ Hosting | Twój komputer z Windowsem (później ewentualnie stary laptop / Raspberry Pi) | 0 zł |

**Łącznie: ~10–30 zł miesięcznie** — praktycznie tylko za API Claude.

> ⚠️ API Claude to osobny rachunek, niezależny od subskrypcji Claude Pro/Max. Płacisz za faktyczne zużycie (console.anthropic.com).

---

## 🏗️ Architektura

```
Ty (Telegram: tekst / głosówka)
        │
        ▼
  Bot w Pythonie (na Twoim PC z Windowsem)
   ├─ głosówka → ffmpeg → Whisper → tekst
   ├─ tekst + pamięć + narzędzia → Claude Haiku
   ├─ odpowiedź → tekst (+ opcjonalnie Piper → głosówka)
   └─ SQLite: pamięć, notatki, przypomnienia
```

---

## 📋 Plan działania

### Etap 0 — Przygotowanie (~30 min, 0 zł)

1. **Bot Telegram:** w Telegramie napisz do **@BotFather** → `/newbot` → zapisz **token bota**.
2. **Twoje Telegram ID:** napisz do **@userinfobot** → zapisz swoje ID (do whitelisty).
3. **Klucz API Claude:** załóż konto na **console.anthropic.com**, doładuj **5 $**, wygeneruj klucz API i **ustaw limit wydatków** (np. 5 $/mies.).
4. **Python na Windowsie:** pobierz Python 3.11+ z python.org — przy instalacji **zaznacz „Add Python to PATH”**.
5. **ffmpeg** (do konwersji głosówek z Telegrama): w PowerShellu `winget install ffmpeg`.
6. **Git** (opcjonalnie, do repo): `winget install Git.Git`.

### Etap 1 — Jarvis MVP: tekst w Telegramie (1 wieczór)

- Bot odbiera wiadomości → wysyła do Claude Haiku → odpisuje.
- Osobowość Jarvisa w system prompcie: lekko sarkastyczny brytyjski lokaj, mówi po polsku, zwraca się „sir” 😏
- 🔒 **Whitelist** — bot odpowiada **tylko na Twoje Telegram ID** (inaczej ktoś obcy przepali Ci kasę).
- Historia ograniczona do ostatnich ~10 wiadomości (oszczędność tokenów).
- Komendy: `/start`, `/reset` (czyści rozmowę), `/koszt` (zużycie tokenów).

### Etap 2 — Pamięć (1 wieczór)

- Baza **SQLite**: fakty o Tobie („lubi X”, „pracuje w Y”), notatki.
- Starsze rozmowy → krótkie **podsumowanie** zamiast całej historii (największa oszczędność).
- **Prompt caching** stałych instrukcji → jeszcze taniej.

### Etap 3 — Głos (1–2 wieczory)

- Wysyłasz głosówkę w Telegramie → ffmpeg + Whisper (lokalnie) → tekst → Jarvis odpowiada.
- Opcjonalnie odpowiedź głosówką przez **Piper TTS** (ma gotowe binarki na Windowsa i polskie głosy).
- Komenda `/glos on` / `/glos off` przełącza tryb odpowiedzi.
- Model Whispera `small` lub `base` — dobry kompromis szybkość/jakość na zwykłym PC (CPU).

### Etap 4 — Narzędzia: Jarvis coś robi (po kawałku)

Wszystko w darmowych wersjach:

- ⏰ **Przypomnienia** — „przypomnij mi jutro o 9 o dentyście” (APScheduler + SQLite, przetrwają restart).
- 🌤️ **Pogoda** — Open-Meteo (darmowe, bez klucza).
- 📝 **Notatki i listy** — zakupy, TODO.
- 💱 **Waluty** — darmowe API NBP.
- 🧮 **Obliczenia, data/godzina.**
- 🔎 **Wyszukiwanie w necie** — wbudowane w Claude, ale dodatkowo płatne → tylko na żądanie.

### Etap 5 — Jarvis proaktywny

- ☀️ Codzienny **poranny brief** na Telegramie: pogoda, przypomnienia na dziś (później kalendarz).
- Sam się odzywa, gdy zbliża się coś zaplanowanego.

### Etap 6 — Bajery na później (opcjonalnie)

- 💻 **Sterowanie Windowsem** — „odpal Spotify”, „wycisz kompa”, „zablokuj ekran”, „zrób screenshota” (tylko z Twojego ID + potwierdzenie dla ryzykownych akcji).
- 📅 Google Calendar / Gmail.
- 🏠 Smart home (Home Assistant).
- 🎤 Wake word „Jarvis” na mikrofonie w pokoju.
- 🔵 HUD z reaktorem łukowym w przeglądarce.
- 🕐 Praca 24/7 na osobnym sprzęcie (Raspberry Pi / stary laptop).

---

## 🪟 Windows — rzeczy do ogarnięcia

- **Środowisko wirtualne** (PowerShell):
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
  Jeśli PowerShell blokuje skrypt: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **Autostart z Windowsem** — Harmonogram zadań (Task Scheduler) albo skrót `.bat` w folderze `shell:startup`.
- **Działanie w tle** — uruchamianie przez `pythonw.exe` (bez okna konsoli).
- **Uśpienie komputera** — jeśli Jarvis ma odpowiadać cały czas, wyłącz usypianie w ustawieniach zasilania (albo zaakceptuj, że działa tylko gdy PC jest włączony).

---

## 💰 Jak trzymać koszty nisko

1. Domyślnie **Haiku 4.5**.
2. Krótka historia + podsumowania zamiast pełnych logów.
3. **Prompt caching** stałych instrukcji.
4. **Limit wydatków** w konsoli Anthropic.
5. **Whitelist** — tylko Twoje Telegram ID.
6. Whisper i Piper **lokalnie** — zero płatnych usług w chmurze.
7. Wyszukiwanie w necie tylko na wyraźne żądanie.

---

## 📁 Struktura projektu

```
Jarvis/
├── jarvis/
│   ├── bot.py          # Telegram (python-telegram-bot)
│   ├── brain.py        # Claude (anthropic SDK)
│   ├── memory.py       # SQLite + podsumowania
│   ├── voice.py        # Whisper + Piper
│   ├── config.py       # wczytywanie .env
│   └── tools/          # pogoda, przypomnienia, notatki, waluty...
├── data/               # baza SQLite, modele głosu (poza gitem)
├── .env                # tokeny i klucze — NIGDY do gita!
├── .env.example        # wzór pliku .env
├── .gitignore
├── requirements.txt
├── start_jarvis.bat    # odpalanie jednym kliknięciem
└── README.md
```

---

## ✅ Checklista postępów

- [ ] Etap 0 — Przygotowanie (token bota, ID, klucz API, Python, ffmpeg)
- [ ] Etap 1 — MVP tekstowy w Telegramie
- [ ] Etap 2 — Pamięć
- [ ] Etap 3 — Głos
- [ ] Etap 4 — Narzędzia
- [ ] Etap 5 — Poranny brief
- [ ] Etap 6 — Bajery
