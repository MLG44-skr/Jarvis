# 💎 MLG Personal Assistant

Osobisty asystent AI w klimacie Jarvisa z Iron Mana. Gadasz z nim przez **Telegram** (telefon albo komputer), a mózg chodzi **lokalnie na Twoim PC** przez **Ollamę**, więc kosztuje 0 zł.

Pełny plan: [`PLAN.md`](PLAN.md) / [`Plan_Jarvis.pdf`](Plan_Jarvis.pdf)

## ✨ Co już umie
- 💬 Gada po polsku na Telegramie (tylko z Tobą, bo ma whitelistę)
- 🧠 **Uczy się Ciebie**: sam zapamiętuje fakty z rozmów, pamięć przetrwa restart
- ⏰ Przypomnienia („przypomnij mi jutro o 9 o dentyście”)
- 📝 Listy („dodaj mleko do zakupów”, „co mam na liście zakupów?”)
- 🌤️ Pogoda (Open-Meteo) i 💱 kursy walut (NBP), darmowe i bez kluczy
- 🧮 Kalkulator
- ☀️ Poranny brief o stałej godzinie: pogoda, plan dnia, listy

---

## 🚀 Odpalenie na Windowsie

### 1. Wymagania
- **Ollama** z modelem `qwen2.5:7b`. Sprawdzenie w PowerShellu: `ollama list`
- **Python 3.11+** z python.org (przy instalacji zaznacz **„Add Python to PATH”**)
- **Bot w Telegramie**: napisz do **@BotFather**, wpisz `/newbot` i skopiuj token

### 2. Pobierz projekt
```powershell
git clone https://github.com/MLG44-skr/Jarvis.git
cd Jarvis
```
(albo na GitHubie: **Code → Download ZIP** i rozpakuj)

### 3. Ustaw `.env`
Skopiuj `.env.example` jako `.env` i uzupełnij:
```
TELEGRAM_TOKEN=123456:ABC...
ALLOWED_USER_IDS=
DEFAULT_CITY=Warszawa
BRIEF_TIME=07:30
```

### 4. Odpal
Kliknij dwa razy **`start_mlg.bat`**. Za pierwszym razem sam zainstaluje potrzebne biblioteki.

### 5. Wpisz swoje ID
Napisz cokolwiek do swojego bota w Telegramie. Odpisze **„Brak dostępu. Twoje Telegram ID: …”**.
Wpisz to ID w `.env` jako `ALLOWED_USER_IDS`, zamknij okno MLG i odpal `start_mlg.bat` jeszcze raz.

Gotowe. Pisz do MLG z telefonu 💎

---

## 💬 Komendy
| Komenda | Co robi |
|---|---|
| `/start` | powitanie i lista komend |
| `/pamiec` | co MLG o Tobie wie |
| `/zapamietaj <tekst>` | każ mu coś zapamiętać |
| `/zapomnij <numer>` | usuń fakt z pamięci (numer z `/pamiec`) |
| `/przypomnienia` | zaplanowane przypomnienia |
| `/brief` | poranny brief od razu |
| `/reset` | czyści rozmowę (pamięć o Tobie zostaje) |
| `/model` | na jakim mózgu jedzie MLG |

Resztę mówisz normalnie: „przypomnij mi za 20 minut o pizzy”, „jaka pogoda w Gdańsku?”, „ile to 15% z 240?”, „po ile euro?”.

## 🛠️ Problemy
- **„Nie mogę się połączyć z Ollamą”**: Ollama nie chodzi. Odpal ją z menu Start (ikonka w trayu).
- **„Ollama nie ma modelu…”**: wpisz `ollama pull qwen2.5:7b`.
- **Pierwsza odpowiedź długo się ładuje**: normalka, Ollama ładuje model do pamięci. Następne są szybsze.
- **MLG nie odpowiada, gdy komp śpi**: wyłącz usypianie w ustawieniach zasilania Windowsa.
- **Wtrąca angielski/chiński**: zdarza się małym modelom. Pomaga `/reset`.

## 🧪 Testy (dla ciekawych)
```powershell
pip install -r requirements-dev.txt
python -m pytest tests
```

## 📁 Struktura
```
mlg/
├── bot.py          # Telegram + komendy
├── agent.py        # pętla: mózg myśli i używa narzędzi
├── brain/          # mózg (Ollama, później opcjonalnie Claude)
├── memory.py       # pamięć SQLite (fakty, rozmowa, listy, przypomnienia)
├── tools/          # narzędzia: pogoda, waluty, kalkulator, listy, przypomnienia
├── brief.py        # poranny brief
├── reminders.py    # pętla w tle (przypomnienia + brief)
├── persona.py      # osobowość MLG
└── config.py       # ustawienia z .env
design/
└── hud-prototyp.dc.html   # prototyp wyglądu HUD-a na pulpit
tests/              # testy
```
Pamięć MLG leży w `data/mlg.db` (poza gitem). Usuniesz ten plik, a MLG zapomni wszystko.
