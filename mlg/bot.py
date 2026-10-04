"""Bot Telegram: tu MLG odbiera i wysyła wiadomości."""

import logging
from collections import defaultdict, deque

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from mlg.brain import Brain, BrainError, Message, OllamaBrain
from mlg.config import Config, load_config
from mlg.persona import system_prompt

log = logging.getLogger("mlg")

TELEGRAM_LIMIT = 4096


class MLGBot:
    def __init__(self, config: Config, brain: Brain):
        self.config = config
        self.brain = brain
        self.history: dict[int, deque[Message]] = defaultdict(lambda: deque(maxlen=config.history_limit))

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

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        await update.message.reply_text(
            "Siema, szefie. MLG Personal Assistant online. 💎\n\n"
            "Pisz normalnie, a ja ogarnę.\n"
            "/reset czyści rozmowę\n"
            "/model pokazuje, na jakim mózgu jadę"
        )

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        self.history.pop(update.effective_chat.id, None)
        await update.message.reply_text("Czysta karta, szefie. Zaczynamy od nowa.")

    async def model(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)
        await update.message.reply_text(f"Mózg: {self.brain.name}")

    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._allowed(update):
            return await self._deny(update)

        chat_id = update.effective_chat.id
        text = update.message.text
        history = self.history[chat_id]

        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        messages: list[Message] = [{"role": "system", "content": system_prompt()}, *history, {"role": "user", "content": text}]

        try:
            answer = await self.brain.chat(messages)
        except BrainError as e:
            log.error("Błąd mózgu: %s", e)
            await update.message.reply_text(f"⚠️ {e}")
            return

        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": answer})

        for i in range(0, len(answer), TELEGRAM_LIMIT):
            await update.message.reply_text(answer[i : i + TELEGRAM_LIMIT])


def build_app(config: Config) -> Application:
    brain = OllamaBrain(config.ollama_url, config.ollama_model, config.ollama_num_ctx)
    bot = MLGBot(config, brain)

    async def on_shutdown(app: Application) -> None:
        await brain.close()

    app = ApplicationBuilder().token(config.telegram_token).post_shutdown(on_shutdown).build()
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("reset", bot.reset))
    app.add_handler(CommandHandler("model", bot.model))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.message))
    return app


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    config = load_config()
    if not config.allowed_user_ids:
        log.warning("ALLOWED_USER_IDS jest puste: MLG nikomu nie odpowie. Napisz do bota, a poda Ci Twoje ID.")

    log.info("MLG startuje. Mózg: Ollama · %s @ %s", config.ollama_model, config.ollama_url)
    build_app(config).run_polling(allowed_updates=Update.ALL_TYPES)
