from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TELEGRAM_BOT_TOKEN
from handlers import handle_message_or_callback

def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text("Привет! Отправьте ссылку на трек или альбом Яндекс.Музыки или просто введите поисковый запрос.")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_or_callback))
    app.add_handler(CallbackQueryHandler(handle_message_or_callback))

    app.run_polling()

if __name__ == '__main__':
    main()
