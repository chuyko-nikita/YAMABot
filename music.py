import os
import re
import requests
from telegram import Update, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from yandex_music import Client

TELEGRAM_BOT_TOKEN = '7796497784:AAF-DvoHqlhZO1RmFDcF27ZKOjsLCjAyT9E'
YANDEX_MUSIC_TOKEN = 'y0_AgAAAAAhRQQbAAG8XgAAAAEWC1zcAABJNcOLbJRM_qAP_llcx7MEZFwFzg' 

try:
    client = Client(YANDEX_MUSIC_TOKEN).init()
    print("Клиент Яндекс.Музыки инициализирован успешно.")
except Exception as e:
    print(f"Ошибка инициализации клиента Яндекс.Музыки: {e}")
    exit(1)


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Привет! Отправьте ссылку на трек Яндекс.Музыки, и я его скачаю (в оригинальном формате, если возможно).')


def extract_track_id(url: str) -> str:
    match = re.search(r'/track/(\d+)', url)
    return match.group(1) if match else None


async def download_song(track_id: str) -> str:
    try:
        print(f"Попытка скачать трек с ID: {track_id}")
        track_list = client.tracks([track_id])
        if not track_list:
            print(f"Трек с ID {track_id} не найден.")
            return None

        track = track_list[0]
        download_info = await track.get_download_info()
        if not download_info:
            return None

        direct_link = await download_info.get_direct_link_async()
        if not direct_link:
            return None
        return direct_link

    except Exception as e:
        print(f"Ошибка при скачивании трека: {e}")
        return None


async def handle_message(update: Update, context: CallbackContext) -> None:
    url = update.message.text.strip()
    track_id = extract_track_id(url)

    if track_id:
        print(f"Извлечен ID трека: {track_id}")
        download_url = await download_song(track_id)
        if download_url:
            try:
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                content_type = response.headers.get('content-type')
                if content_type:
                    filename = f"track_{track_id}.{content_type.split('/')[-1]}"
                    await update.message.reply_document(document=response.raw, filename=filename,
                                                        caption=f"Вот ваш трек: Ссылка",
                                                        parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text("Не удалось определить тип файла.")

            except requests.exceptions.RequestException as e:
                await update.message.reply_text(f"Ошибка загрузки: {e}")
        else:
            await update.message.reply_text('Не удалось скачать песню. Убедитесь, что ID трека корректен.')
    else:
        await update.message.reply_text('Пожалуйста, отправьте корректную ссылку на трек Яндекс.Музыки.')


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == '__main__':
    main()
