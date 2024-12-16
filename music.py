import os
import re
import asyncio
import io
from mutagen import File
from mutagen.id3 import TIT2, TPE1, TALB, APIC, TDRC, USLT
from yandex_music import Client, Playlist, SearchResult
from yandex_music.exceptions import YandexMusicError
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message # Добавлено
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler


TELEGRAM_BOT_TOKEN = '7796497784:AAF-DvoHqlhZO1RmFDcF27ZKOjsLCjAyT9E'
YANDEX_MUSIC_TOKEN = 'y0_AgAAAAAhRQQbAAG8XgAAAAEWC1zcAABJNcOLbJRM_qAP_llcx7MEZFwFzg'

DELIMITER = "/"

def strip_bad_symbols(text: str) -> str:
    result = re.sub(r"[^\w_.)( -]", "", text)
    return result

def extract_track_id(text: str) -> str:
    match = re.search(r'/track/(\d+)', text)
    if match:
        return match.group(1)
    match = re.search(r'(\d+)', text)  # Попытка извлечь track_id из текста кнопки
    if match:
        return match.group(1)
    return None #Возвращение None


async def download_and_send_track(message: Message, context: CallbackContext, track_id: str):
    if message is None:
        print("Ошибка: message равен None в download_and_send_track")
        return

    print(f"Type of message in download_and_send_track: {type(message)}")  # Для отладки

    try:
        client = Client(YANDEX_MUSIC_TOKEN).init()
        track = client.tracks([track_id])[0]
        track_title = track.title
        track_performer = ', '.join([artist.name for artist in track.artists]) if track.artists else "Неизвестный исполнитель"
        file_name = strip_bad_symbols(track_title)

        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        os.chdir(temp_dir)

        for info in sorted(track.get_download_info(), key=lambda x: x['bitrate_in_kbps'], reverse=True):
            codec = info['codec']
            full_file_name = f'{file_name}.{codec}'
            try:
                track.download(full_file_name, codec=codec)
                break
            except (YandexMusicError, TimeoutError) as e:
                print(f"Ошибка загрузки: {e}")
                continue
        else:
            print("Не удалось скачать трек.")
            return

        cover_filename = file_name + ".jpg"
        try:
            track.download_cover(cover_filename, size="300x300")
        except Exception as e:
            print(f"Ошибка загрузки обложки: {e}")
            await message.reply_text(f"Ошибка загрузки обложки: {e}")
            return

        file = File(f'{file_name}.{codec}')
        file.update({
            'TIT2': TIT2(encoding=3, text=track_title),
            'TPE1': TPE1(encoding=3, text=track_performer),
            'TALB': TALB(encoding=3, text=track.albums[0]['title'] if track.albums else "Неизвестный альбом"),
            'TDRC': TDRC(encoding=3, text=str(track.albums[0]['year']) if track.albums and track.albums[0]['year'] else "Неизвестный год"),
            'APIC': APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=open(cover_filename, 'rb').read())
        })
        lyrics = client.track_supplement(track.track_id).lyrics
        if lyrics:
            file.tags.add(USLT(encoding=3, text=lyrics.full_lyrics))
        file.save()

        with open(f'{file_name}.{codec}', 'rb') as audio_file, open(cover_filename, 'rb') as cover_file:
            await message.reply_audio(
                audio=audio_file,
                performer=track_performer,
                title=track_title,
                thumb=InputFile(cover_file)
            )

        os.remove(f'{file_name}.{codec}')
        os.remove(cover_filename)
        os.chdir("..")

    except Exception as e:
        await message.reply_text(f"Ошибка: {e}")
        print(f"Полное исключение: {e}")


async def search_track(update: Update, context: CallbackContext) -> None:
    if update is None or update.message is None:
        print("Ошибка: update или update.message равны None в search_track")
        return

    query = update.message.text.strip().split('/search ', 1)[1]
    if not query:
        await update.message.reply_text("Пожалуйста, введите поисковый запрос после '/search'.")
        return
    print(f"Поисковый запрос: {query}")

    try:
        client = Client(YANDEX_MUSIC_TOKEN).init()
        search_result = client.search(query)
        print(f"Количество треков: {search_result.tracks.total if search_result.tracks else 0}")

        if search_result.tracks and search_result.tracks.total > 0:
            keyboard = []
            for track in search_result.tracks.results[:5]:
                button = InlineKeyboardButton(
                    text=f"{track.title} - {', '.join([artist.name for artist in track.artists]) if track.artists else 'Неизвестный исполнитель'}",
                    callback_data=track.track_id
                )
                keyboard.append([button])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Вот что мне удалось найти:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("К сожалению, ничего не найдено.")

    except Exception as e:
        await update.message.reply_text(f"Ошибка поиска: {e}")
        print(f"Ошибка поиска: {e}")



async def handle_message_or_callback(update: Update, context: CallbackContext) -> None:
    if isinstance(update, Update) and isinstance(update.callback_query, CallbackQuery):
        query = update.callback_query
        message = query.message
        await query.answer()
        track_id = query.data
    elif isinstance(update, Update) and isinstance(update.message, Message):
        message = update.message
        track_id = extract_track_id(message.text)
    else:
        return

    if track_id:
        try:
            await download_and_send_track(message, context, track_id)
        except Exception as e:
            await message.reply_text(f"Ошибка при загрузке трека: {e}")
    else:
        await message.reply_text("Не удалось извлечь ID трека.")


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text("Привет! Отправьте ссылку на трек Яндекс.Музыки или используйте команду /search <запрос>.")))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'/search .+'), search_track))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_or_callback))
    app.add_handler(CallbackQueryHandler(handle_message_or_callback))

    app.run_polling()


if __name__ == '__main__':
    main()
