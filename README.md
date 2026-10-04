# 💎 MLG Personal Assistant

Osobisty asystent AI w klimacie Jarvisa z Iron Mana. Gadasz z nim przez **Telegram** (telefon albo komputer), a mózg chodzi **lokalnie na Twoim PC** przez **Ollamę**, więc kosztuje 0 zł.

Pełny plan: [`PLAN.md`](PLAN.md) / [`Plan_Jarvis.pdf`](Plan_Jarvis.pdf)

---

## 🚀 Odpalenie na Windowsie (Etap 1)

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
Skopiuj `.env.example` jako `.env` i wklej token od BotFathera:
```
TELEGRAM_TOKEN=123456:ABC...
ALLOWED_USER_IDS=
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
| `/start` | powitanie |
| `/reset` | czyści rozmowę |
| `/model` | pokazuje, na jakim mózgu jedzie MLG |

## 🛠️ Problemy
- **„Nie mogę się połączyć z Ollamą”**: Ollama nie chodzi. Odpal ją z menu Start (ikonka w trayu).
- **„Ollama nie ma modelu…”**: wpisz `ollama pull qwen2.5:7b`.
- **Pierwsza odpowiedź długo się ładuje**: normalka, Ollama ładuje model do pamięci. Następne są szybsze.
- **MLG nie odpowiada, gdy komp śpi**: wyłącz usypianie w ustawieniach zasilania Windowsa.

## 📁 Struktura
```
mlg/
├── bot.py          # Telegram
├── brain/          # mózg (Ollama, później opcjonalnie Claude)
├── config.py       # ustawienia z .env
└── persona.py      # osobowość MLG
design/
└── hud-prototyp.dc.html   # prototyp wyglądu HUD-a na pulpit
```
