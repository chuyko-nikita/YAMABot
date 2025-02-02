from telegram import Update
from telegram.ext import CallbackContext
from utils import extract_track_id, extract_album_id
from music import download_and_send_track, send_album_tracks, search_track_or_album

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
