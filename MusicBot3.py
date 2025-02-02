import os
import re
import asyncio
from io import BytesIO
from mutagen import File
from mutagen.id3 import TIT2, TPE1, TALB, APIC, TDRC, USLT
from yandex_music import Client, Playlist, SearchResult, Album
from yandex_music.exceptions import YandexMusicError
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YANDEX_MUSIC_TOKEN = os.getenv('YANDEX_MUSIC_TOKEN')

if TELEGRAM_BOT_TOKEN is None or YANDEX_MUSIC_TOKEN is None:
    raise ValueError("Один или оба токена не установлены в переменных окружения!")

DELIMITER = "/"

def strip_bad_symbols(text: str) -> str:
    result = re.sub(r"[^\w_.)( -]", "", text)
    return result

def extract_track_id(text: str) -> str:
    patterns = [
        r'https?://music\.yandex\.ru/album/\d+/track/(\d+)(?:\?.*)?',
        r'https?://music\.yandex\.ru/track/(\d+)(?:\?.*)?',
        r'/track/(\d+)(?:\?.*)?',
        r'track/(\d+)(?:\?.*)?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

def extract_album_id(text: str) -> str:
    patterns = [
        r'https?://music\.yandex\.ru/album/(\d+)(?:\?.*)?',
        r'/album/(\d+)(?:\?.*)?',
        r'album/(\d+)(?:\?.*)?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

async def download_and_send_track(message: Message, context: CallbackContext, track_id: str):
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

async def send_album_tracks(message: Message, context: CallbackContext, album_id: str):
    try:
        client = Client(YANDEX_MUSIC_TOKEN).init()
        album = client.albums_with_tracks(album_id)

        if album:
            keyboard = []
            for volume in album.volumes:
                for track in volume:
                    button = InlineKeyboardButton(
                        text=f"{track.title} - {', '.join([artist.name for artist in track.artists])}",
                        callback_data=track.track_id
                    )
                    keyboard.append([button])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text(f"Треки альбома '{album.title}':", reply_markup=reply_markup)
        else:
            await message.reply_text("Альбом не найден.")
    except Exception as e:
        await message.reply_text(f"Ошибка при обработке альбома: {e}")

async def search_track_or_album(message: Message, context: CallbackContext, query: str) -> None:
    if not query:
        await message.reply_text("Пожалуйста, введите поисковый запрос.")
        return
    print(f"Поисковый запрос: {query}")

    try:
        client = Client(YANDEX_MUSIC_TOKEN).init()
        search_result = client.search(query)

        keyboard = []
        if search_result.tracks and search_result.tracks.total > 0:
            for track in search_result.tracks.results[:5]:
                button = InlineKeyboardButton(
                    text=f"{track.title} - {', '.join([artist.name for artist in track.artists])}",
                    callback_data=track.track_id
                )
                keyboard.append([button])
        if search_result.albums and search_result.albums.total > 0:
            for album in search_result.albums.results[:5]:
                button = InlineKeyboardButton(
                    text=f"Альбом: {album.title} - {', '.join([artist.name for artist in album.artists])}",
                    callback_data=f"album_{album.id}"
                )
                keyboard.append([button])

        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text("Результаты поиска:", reply_markup=reply_markup)
        else:
            await message.reply_text("К сожалению, ничего не найдено.")

    except Exception as e:
        await message.reply_text(f"Ошибка поиска: {e}")
        print(f"Ошибка поиска: {e}")

async def handle_message_or_callback(update: Update, context: CallbackContext) -> None:
    if update.callback_query:
        query = update.callback_query
        message = query.message
        await query.answer()
        data = query.data
        if data.startswith("album_"):
            album_id = data[6:]
            await send_album_tracks(message, context, album_id)
        else:
            await download_and_send_track(message, context, data)
    elif update.message:
        message = update.message
        text = message.text.strip()
        track_id = extract_track_id(text)
        album_id = extract_album_id(text)
        if track_id:
            await download_and_send_track(message, context, track_id)
        elif album_id:
            await send_album_tracks(message, context, album_id)
        else:
            await search_track_or_album(message, context, text)
    else:
        return

def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", lambda update, context: update.message.reply_text("Привет! Отправьте ссылку на трек или альбом Яндекс.Музыки или просто введите поисковый запрос.")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_or_callback))
    app.add_handler(CallbackQueryHandler(handle_message_or_callback))

    app.run_polling()

if __name__ == '__main__':
    main()
