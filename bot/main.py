import logging

from telegram.ext import Application, CommandHandler

from bot.config import BOT_TOKEN
from bot.handlers.brand import build_brand_conversation
from bot.handlers.driver import build_driver_conversation
from bot.handlers.start import start

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(build_driver_conversation())
    app.add_handler(build_brand_conversation())

    logger.info("🚖 WB TAXI HUMO bot ishga tushdi...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
