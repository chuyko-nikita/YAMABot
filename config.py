import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YANDEX_MUSIC_TOKEN = os.getenv('YANDEX_MUSIC_TOKEN')

if TELEGRAM_BOT_TOKEN is None or YANDEX_MUSIC_TOKEN is None:
    raise ValueError("Один или оба токена не установлены в переменных окружения!")

DELIMITER = "/"
