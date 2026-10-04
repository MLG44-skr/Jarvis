"""Bot Telegram: tu MLG odbiera i wysyła wiadomości."""

import logging

import httpx
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from mlg.brain import Brain, BrainError, OllamaBrain
from mlg.brief import build_brief, parse_brief_time
from mlg.config import Config, load_config
from mlg.core import MLGCore
from mlg.hud.server import HUDServer
from mlg.memory import Memory
from mlg.reminders import background_loop

log = logging.getLogger("mlg")

TELEGRAM_LIMIT = 4096


class MLGBot:
    def __init__(self, config: Config, brain: Brain, memory: Memory, http: httpx.AsyncClient, core: MLGCore | None = None):
        self.config = config
        self.brain = brain
        self.memory = memory
        self.http = http
        self.core = core or MLGCore(config, brain, memory, http)

    def _allowed(self, update: Update) -> bool:
        user = update.effective_user
        return user is not None and user.id in self.config.allowed_user_ids

    async def _deny(self, update: Update) -> None:
        user = update.effective_user
        uid = user.id if user else "?"
        log.warning("Odmowa dostępu dla ID %s (%s)", uid, user.username if user else "?")
        await update.effective_message.reply_text(
            f"Brak dostępu. Twoje Telegram ID: {uid}\n"
            "Jeśli to Ty jesteś szefem, wpisz je w pliku .env jako ALLOWED_USER_IDS i zrestartuj MLG."
        )

    @staticmethod
    async def _send(update: Update, text: str) -> None:
        for i in range(0, len(text), TELEGRAM_LIMIT):
            await update.message.reply_text(text[i : i + TELEGRAM_LIMIT])

    # --- komendy ---

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        await update.message.reply_text(
            "Siema, szefie. MLG Personal Assistant online. 💎\n\n"
            "Pisz normalnie, a ja ogarnę: przypomnienia, listy, pogodę, kursy walut, obliczenia. "
            "Uczę się też Ciebie, więc im więcej gadamy, tym lepiej Cię znam.\n\n"
            "/pamiec – co o Tobie wiem\n"
            "/zapamietaj <tekst> – każ mi coś zapamiętać\n"
            "/zapomnij <numer> – usuń coś z pamięci\n"
            "/przypomnienia – zaplanowane przypomnienia\n"
            "/brief – poranny brief teraz\n"
            "/reset – czyści rozmowę (pamięć zostaje)\n"
            "/model – na jakim mózgu jadę"
        )

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        self.memory.clear_history(update.effective_user.id)
        await update.message.reply_text("Czysta karta, szefie. Rozmowa wyczyszczona, ale to, co o Tobie wiem, zostaje.")

    async def model(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        await update.message.reply_text(f"Mózg: {self.brain.name}")

    async def pamiec(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        facts = self.memory.facts(update.effective_user.id)
        if not facts:
            await update.message.reply_text("Jeszcze nic o Tobie nie wiem, szefie. Opowiadaj.")
            return
        lines = [f"#{f.id} {f.text}" for f in facts]
        await self._send(update, "Co o Tobie wiem:\n" + "\n".join(lines) + "\n\nUsuwanie: /zapomnij <numer>")

    async def zapamietaj(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        text = " ".join(context.args or []).strip()
        if not text:
            await update.message.reply_text("Co mam zapamiętać? Np. /zapamietaj lubię pizzę hawajską")
            return
        fact = self.memory.add_fact(update.effective_user.id, text)
        await update.message.reply_text(f"Zapamiętane (#{fact.id}).")

    async def zapomnij(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        arg = (context.args or [""])[0].lstrip("#")
        if not arg.isdigit():
            await update.message.reply_text("Podaj numer z /pamiec, np. /zapomnij 3")
            return
        ok = self.memory.forget_fact(update.effective_user.id, int(arg))
        await update.message.reply_text("Zapomniane, szefie. 🫡" if ok else f"Nie mam w pamięci #{arg}.")

    async def przypomnienia(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        items = self.memory.pending_reminders(update.effective_user.id)
        if not items:
            await update.message.reply_text("Nie masz zaplanowanych przypomnień.")
            return
        lines = [f"#{r.id} {r.due_at:%d.%m %H:%M}: {r.text}" for r in items]
        await self._send(update, "Zaplanowane:\n" + "\n".join(lines))

    async def brief(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        text = await build_brief(self.memory, self.http, update.effective_user.id, self.config.default_city)
        await self._send(update, text)

    # --- zwykłe wiadomości ---

    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)

        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        try:
            answer = await self.core.ask(update.effective_user.id, chat_id, update.message.text)
        except BrainError as e:
            log.error("Błąd mózgu: %s", e)
            await update.message.reply_text(f"⚠️ {e}")
            return
        await self._send(update, answer)


def build_app(config: Config) -> Application:
    brain = OllamaBrain(
        config.ollama_url, config.ollama_model, config.ollama_num_ctx,
        think=config.ollama_think, temperature=config.ollama_temperature,
    )
    memory = Memory(config.data_dir / "mlg.db")
    http = httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "MLG-Personal-Assistant"})
    core = MLGCore(config, brain, memory, http)
    bot = MLGBot(config, brain, memory, http, core=core)
    hud = HUDServer(core, config.hud_host, config.hud_port) if config.hud_port else None

    brief_at = parse_brief_time(config.brief_time)

    async def on_start(app: Application) -> None:
        app.create_task(background_loop(app, memory, http, config.allowed_user_ids, config.default_city, brief_at))
        if hud:
            await hud.start()
            if config.hud_auto_open:
                hud.open_in_browser()

    async def on_shutdown(app: Application) -> None:
        if hud:
            await hud.stop()
        await brain.close()
        await http.aclose()
        memory.close()

    app = ApplicationBuilder().token(config.telegram_token).post_init(on_start).post_shutdown(on_shutdown).build()
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("reset", bot.reset))
    app.add_handler(CommandHandler("model", bot.model))
    app.add_handler(CommandHandler("pamiec", bot.pamiec))
    app.add_handler(CommandHandler("zapamietaj", bot.zapamietaj))
    app.add_handler(CommandHandler("zapomnij", bot.zapomnij))
    app.add_handler(CommandHandler("przypomnienia", bot.przypomnienia))
    app.add_handler(CommandHandler("brief", bot.brief))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message))
    return app


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    config = load_config()
    if not config.allowed_user_ids:
        log.warning("ALLOWED_USER_IDS jest puste: MLG nikomu nie odpowie. Napisz do bota, a poda Ci Twoje ID.")

    log.info("MLG Personal Assistant startuje. Mózg: Ollama · %s @ %s", config.ollama_model, config.ollama_url)
    build_app(config).run_polling(allowed_updates=Update.ALL_TYPES)
