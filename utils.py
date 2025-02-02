import re

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
