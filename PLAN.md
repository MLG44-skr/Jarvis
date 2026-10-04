# 💎 Plan MLG Personal Assistant

Osobisty asystent AI w klimacie Jarvisa z Iron Mana: połączony z Telegramem, działający na Windowsie, z mózgiem na **Ollamie** (lokalnie, za darmo), z własnym HUD-em na pulpit.

---

## 📍 Gdzie jesteśmy

| Etap | Co | Status |
|---|---|---|
| 0 | Przygotowanie (token bota, Python, ffmpeg) | ⏳ **Twoja kolej** |
| 1 | MVP: MLG na Telegramie z Ollamą | ✅ kod gotowy |
| 2 | Pamięć i uczenie się Ciebie | ✅ kod gotowy (nawyki w Etapie 7) |
| 3 | Głos (głosówki w Telegramie) | 🔜 |
| 4 | Narzędzia: przypomnienia, listy, pogoda, waluty, kalkulator | ✅ kod gotowy |
| 5 | Poranny brief | ✅ kod gotowy |
| 6 | HUD na pulpit (turkusowe koło + orbity) | 🎨 prototyp wyglądu gotowy |
| 7 | Sterowanie Windowsem + Twoje apki na orbitach + nawyki | 🔜 |
| 8 | Claude Code: odpalanie projektów + tryb `/madry` | 🔜 |
| 9 | Bajery: wake word, kalendarz, smart home, serwer 24/7 | 🔜 |

✅ = napisane i przetestowane automatycznie (na udawanej Ollamie). Pierwszy test „na żywo” robisz Ty po Etapie 0.

---

## 🎯 Założenia budżetowe

| Element | Rozwiązanie | Koszt |
|---|---|---|
| 🧠 Mózg | **Ollama + `qwen2.5:7b`** lokalnie na Twoim PC | **0 zł** |
| ✨ Mózg „na trudne sprawy” (opcjonalnie) | Claude **Haiku 4.5** ($1 / $5 za 1 mln tokenów), tylko na żądanie komendą `/madry` | 0–10 zł/mies. |
| 🎙️ Słuch | Whisper lokalnie (`faster-whisper`) | 0 zł |
| 🔊 Głos | Piper TTS lokalnie | 0 zł |
| 💬 Interfejs | Telegram Bot API + HUD na pulpicie | 0 zł |
| 🌤️ Pogoda / 💱 waluty | Open-Meteo / NBP | 0 zł |
| 🖥️ Hosting | Twój komputer z Windowsem | 0 zł (+ prąd) |

**Łącznie: 0 zł miesięcznie.**

> ⚠️ API Claude to osobny rachunek, niezależny od subskrypcji Claude Pro/Max. Całkowicie opcjonalne.

### Ollama vs Claude: uczciwie

| | Ollama (`qwen2.5:7b`) | Claude Haiku 4.5 |
|---|---|---|
| Koszt | 0 zł | grosze za rozmowę |
| Prywatność | 100%, nic nie wychodzi z PC | tekst idzie do API |
| Inteligencja | OK do gadki, notatek, przypomnień | dużo bystrzejszy |
| Polski | dobry, czasem wtrąca angielski/chiński | bardzo dobry |
| Bez internetu | ✅ (poza samym Telegramem) | ❌ |

---

## 🏗️ Architektura

```
📱 Ty (Telegram: tekst / głosówka, z dowolnego miejsca)
        │
        ▼
☁️ Serwery Telegrama
        │
        ▼
🖥️ MLG na Twoim PC z Windowsem
   ├─ głosówka → ffmpeg → Whisper → tekst          (Etap 3)
   ├─ agent: tekst + pamięć + narzędzia → MÓZG
   │     ├─ domyślnie: Ollama (qwen2.5:7b) @ localhost:11434
   │     └─ /madry:    Claude (opcjonalnie)          (Etap 8)
   ├─ narzędzia: przypomnienia, listy, pogoda, waluty, kalkulator
   ├─ pętla w tle: przypomnienia + poranny brief
   ├─ HUD na pulpicie (przeglądarka / okno)          (Etap 6)
   └─ SQLite (data/mlg.db): pamięć, rozmowy, listy, przypomnienia
```

- **Działa z telefonu z każdego miejsca** (LTE, cudze WiFi), bez grzebania w routerze.
- **Komp musi być włączony.** Jak śpi, MLG też śpi (wiadomości poczekają). Serwer 24/7 to Etap 9.
- **Mózg jest wymienny**, a kod reszty się nie zmienia.

---

## 📋 Etapy

### Etap 0: Przygotowanie (~20 min, 0 zł) ⏳ TWOJA KOLEJ

1. ✅ **Ollama**: masz.
2. ✅ **Model `qwen2.5:7b`**: masz (sprawdzenie: `ollama list`).
3. **Bot Telegram:** napisz do **@BotFather**, wpisz `/newbot` i zapisz **token**.
4. **Python 3.11+** z python.org. Przy instalacji **zaznacz „Add Python to PATH”**.
5. **Pobierz repo**, skopiuj `.env.example` jako `.env`, wklej token, odpal `start_mlg.bat`.
6. Napisz do bota. Poda Ci Twoje **Telegram ID**, które wpisujesz w `.env` (`ALLOWED_USER_IDS`) i restartujesz.
7. *(Na Etap 3)* **ffmpeg**: `winget install ffmpeg`.

Szczegóły krok po kroku: [`README.md`](README.md).

> 🔐 Tokenów i kluczy nigdy nikomu nie wysyłaj i nie wrzucaj do repo. Trzymamy je tylko w pliku `.env`.

### Etap 1: MVP na Telegramie ✅

- Bot odbiera wiadomości, przekazuje je do Ollamy (`qwen2.5:7b`) i odpisuje.
- Osobowość MLG: ziomek z klasą, mówi „szefie”, krótko i konkretnie.
- 🇵🇱 **Wymuszony polski** w system prompcie.
- ⚙️ `num_ctx` = 8192, żeby nie gubił wątku.
- 🔒 **Whitelist**: odpowiada tylko na Twoje ID, a obcym pokazuje ich ID (tak zdobywasz swoje).
- `start_mlg.bat`: odpalanie jednym kliknięciem, sam instaluje biblioteki.

### Etap 2: Pamięć i uczenie się Ciebie ✅

- Baza **SQLite** w `data/mlg.db`. Przetrwa restart.
- 🧠 **Sam wyłapuje fakty z rozmów** (narzędzie „zapamiętaj”): imię, ludzie, ulubione rzeczy, praca, nawyki.
- Fakty trafiają do każdej rozmowy, więc MLG zna Cię coraz lepiej.
- Historia rozmowy też jest zapisywana (ostatnie ~20 wiadomości).
- `/pamiec`, `/zapamietaj`, `/zapomnij`: pełna kontrola nad tym, co wie.
- `/reset` czyści tylko rozmowę, a wiedza o Tobie zostaje.
- 🔜 Nawyki (co odpalasz i kiedy) dojdą w Etapie 7, razem ze sterowaniem Windowsem.

> Sam model się nie zmienia. MLG uczy się **Ciebie** dzięki pamięci, a nie robi się ogólnie mądrzejszy.

### Etap 3: Głos 🔜

- Wysyłasz głosówkę w Telegramie, ffmpeg i Whisper robią z niej tekst, a MLG odpowiada.
- Opcjonalnie odpowiedź głosówką przez **Piper TTS** (polskie głosy).
- `/glos on` / `/glos off`.
- Whisper `base`/`small` na **CPU**, żeby nie zabierał VRAM Qwenowi.

### Etap 4: Narzędzia ✅

Qwen sam decyduje, kiedy użyć narzędzia (tool calling):

- ⏰ **Przypomnienia**: „przypomnij mi jutro o 9 o dentyście”, „za 20 minut wyjmij pizzę”. Wysyłane w tle, przetrwają restart.
- 📝 **Listy**: zakupy, TODO, filmy (dodaj, pokaż, usuń, wyczyść).
- 🌤️ **Pogoda**: Open-Meteo, teraz + dziś + jutro.
- 💱 **Waluty**: kurs średni NBP.
- 🧮 **Kalkulator**: bezpieczny, nie liczy „na oko”.

### Etap 5: Poranny brief ✅

- Codziennie o `BRIEF_TIME` (np. 07:30): pogoda, przypomnienia na dziś, listy.
- Jak komp był wyłączony rano, brief przyjdzie po włączeniu (raz dziennie).
- `/brief` daje brief od razu.
- 🔜 Proaktywne podpowiedzi („szefie, 20:00, odpalić Discorda?”) w Etapie 7.

### Etap 6: HUD na pulpit 🎨

Prototyp wyglądu jest w [`design/hud-prototyp.dc.html`](design/hud-prototyp.dc.html):

- 🌊 Bardzo ciemny motyw z **turkusem i morską zielenią**.
- ⭕ **Koło jak w Jarvisie**: trzy kręcące się pierścienie i pulsujący rdzeń z napisem **MLG**.
- 🪐 **Twoje rzeczy z kompa latają wokół** na orbitach (apki, foldery, narzędzia).
- ⚡ **Widać, gdzie wchodzi MLG**: przy „odpal spotify” z koła wystrzeliwuje promień do tej rzeczy, a ona się rozświetla.
- 💬 Panel rozmowy zsynchronizowany z Telegramem, status systemu, zasoby PC, ostatnie akcje.

Do zrobienia: prawdziwa wersja, czyli lokalna strona (albo okno pełnoekranowe) podpięta pod MLG na żywo.

### Etap 7: Sterowanie Windowsem + nawyki 🔜

- 💻 „Odpal Spotify”, „otwórz Pobrane”, „wycisz kompa”, „zablokuj ekran”, „zrób screenshota”.
- 🪐 Skan menu Start, pulpitu i ostatnich folderów, żeby na orbitach HUD-a latały **Twoje prawdziwe** apki i foldery.
- 📈 **Nawyki**: MLG widzi, co i kiedy odpalasz. Częste rzeczy lecą bliżej środka, a on sam podpowiada.
- 🔒 Tylko z Twojego ID, a ryzykowne akcje z potwierdzeniem (przyciski Tak/Nie w Telegramie).

### Etap 8: Claude Code + tryb `/madry` 🔜

- 📂 „Odpal projekt X w Claude” otwiera terminal w folderze projektu z Claude Code.
- 📱 Zadanie z telefonu: „niech Claude dopisze Y do projektu X”. MLG odpala `claude -p "..."` w tle i odsyła podsumowanie na Telegrama.
- 🪐 Projekty jako kulki na orbicie HUD-a.
- ✨ `/madry`: trudne pytanie idzie do Claude zamiast Qwena.
- ⚠️ Wymaga subskrypcji Claude (Pro/Max) albo API. Zawsze z potwierdzeniem przed zmianami w kodzie.

### Etap 9: Bajery 🔜

- 🎤 Wake word „MLG” na mikrofonie w pokoju.
- 📅 Google Calendar i Gmail.
- 🏠 Smart home (Home Assistant).
- 🕐 **Serwer 24/7**, żeby MLG działał przy wyłączonym kompie:
  - Oracle Cloud Free Tier (0 zł, wolniejsza Ollama na CPU),
  - tani VPS + Claude Haiku (~20–40 zł/mies., szybki i bystry),
  - Raspberry Pi w domu (jednorazowo kilkaset zł, kilka watów),
  - hybryda: komp włączony = Ollama, wyłączony = Claude.
- 👥 Dostęp dla innych osób (każda z osobną pamięcią).
- 🔄 Test innych modeli: nowszy Qwen, polski Bielik.

---

## 🪟 Windows: rzeczy do ogarnięcia

- **Ollama** chodzi sama w tle (ikonka w trayu) i startuje z systemem.
- **`start_mlg.bat`** sam tworzy środowisko Pythona i instaluje biblioteki.
- **Autostart MLG**: skrót do `start_mlg.bat` w folderze `shell:startup` (Win+R → `shell:startup`).
- **Uśpienie komputera**: do pracy 24/7 wyłącz usypianie w ustawieniach zasilania.

---

## 💰 Jak trzymać koszty (i obciążenie PC) nisko

1. Domyślnie **Ollama**, czyli 0 zł.
2. Claude **tylko na żądanie**, z **limitem wydatków** w konsoli.
3. Krótka historia rozmowy, żeby mały model był szybszy i mądrzejszy.
4. **Whitelist**, czyli tylko Twoje Telegram ID.
5. Whisper na CPU, Ollama na GPU, żeby się nie gryzły.

---

## 📁 Struktura projektu

```
Jarvis/
├── mlg/
│   ├── bot.py            # Telegram + komendy
│   ├── agent.py          # pętla: mózg myśli i używa narzędzi
│   ├── brain/            # Ollama (domyślny), później Claude
│   ├── memory.py         # SQLite: fakty, rozmowy, listy, przypomnienia
│   ├── tools/            # pogoda, waluty, kalkulator (+ listy, przypomnienia)
│   ├── brief.py          # poranny brief
│   ├── reminders.py      # pętla w tle
│   ├── persona.py        # osobowość MLG
│   └── config.py         # ustawienia z .env
├── design/               # prototyp HUD-a
├── tests/                # testy automatyczne
├── data/                 # baza MLG (poza gitem)
├── .env.example          # wzór ustawień
├── start_mlg.bat         # odpalanie jednym kliknięciem
├── PLAN.md / Plan_Jarvis.pdf
└── README.md             # instrukcja odpalenia
```

---

## ✅ Checklista postępów

- [x] Ollama + `qwen2.5:7b` zainstalowane
- [ ] Etap 0: token bota, Python, `.env`, pierwszy start
- [x] Etap 1: MVP na Telegramie (kod)
- [x] Etap 2: Pamięć i uczenie się (kod)
- [ ] Etap 3: Głos
- [x] Etap 4: Narzędzia (kod)
- [x] Etap 5: Poranny brief (kod)
- [ ] Etap 6: HUD na pulpit (prototyp ✅, wersja prawdziwa ⏳)
- [ ] Etap 7: Sterowanie Windowsem + nawyki
- [ ] Etap 8: Claude Code + `/madry`
- [ ] Etap 9: Bajery
