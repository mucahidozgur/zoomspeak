"""Yardımcı fonksiyonlar: zaman damgası biçimlendirme, dosya adı temizleme.

Tamamı saf fonksiyonlardır; dış bağımlılık yoktur.
"""


def format_timestamp(ms: int) -> str:
    """Milisaniyeyi "HH:MM:SS" biçimine çevirir."""
    total_s = max(0, int(ms)) // 1000
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_srt_timestamp(ms: int) -> str:
    """Milisaniyeyi SRT zaman damgasına çevirir: "HH:MM:SS,mmm"."""
    ms = max(0, int(ms))
    total_s, millis = divmod(ms, 1000)
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def format_elapsed(seconds: float) -> str:
    """Geçen süreyi okunabilir biçimde döndürür: "0:45" veya "1:02:33"."""
    total = max(0, int(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


_TR_CHAR_MAP = str.maketrans(
    {
        "ı": "i",
        "ş": "s",
        "ğ": "g",
        "ü": "u",
        "ö": "o",
        "ç": "c",
        "İ": "i",
        "Ş": "s",
        "Ğ": "g",
        "Ü": "u",
        "Ö": "o",
        "Ç": "c",
    }
)


def sanitize_filename(name: str) -> str:
    """Dosya adını küçük harfli, ASCII güvenli hale getirir."""
    cleaned = name.translate(_TR_CHAR_MAP).lower()
    cleaned = "".join(
        c if (c.isalnum() and c.isascii()) or c in "_-" else "_" for c in cleaned
    )
    return cleaned.strip("_") or "transkripsiyon"
