"""İstemci hata yolları ve biçimlendirme modülü için duman testi.

Çalıştırma: py -3 verify_client.py   (401 testi için ağ erişimi gerekir)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.soniox_client import TranscriptionError, transcribe_audio
from src.transcription_service import format_transcript, group_tokens_by_speaker
from src.utils import format_srt_timestamp, format_timestamp, sanitize_filename

failures = 0

Path("temp").mkdir(exist_ok=True)
Path("temp/dummy.wav").write_bytes(b"RIFFxxxxWAVEfmt dummy")  # içerik önemsiz


def expect_error(desc, fn, expected_fragment):
    global failures
    try:
        fn()
    except TranscriptionError as e:
        if expected_fragment in str(e):
            print(f"OK   : {desc}")
        else:
            failures += 1
            print(f"FAIL : {desc} — mesaj uyuşmadı: {e}")
        return
    except Exception as e:  # noqa: BLE001 - beklenmeyen istisna da başarısızlıktır
        failures += 1
        print(f"FAIL : {desc} — beklenmeyen istisna: {type(e).__name__}: {e}")
        return
    failures += 1
    print(f"FAIL : {desc} — hata bekleniyordu, gelmedi")


# 1) Anahtar "test" ile gerçek 401 eşlemesi (ağ gerektirir)
os.environ["SONIOX_API_KEY"] = "test"
os.environ.pop("SONIOX_BASE_URL", None)
expect_error(
    "401: anahtar 'test' -> 'API anahtarı geçersiz'",
    lambda: transcribe_audio("temp/dummy.wav"),
    "API anahtarı geçersiz",
)

# 2) Bağlantı hatası (SONIOX_BASE_URL test kancası)
os.environ["SONIOX_BASE_URL"] = "http://127.0.0.1:9"
expect_error(
    "Bağlantı hatası -> Türkçe mesaj",
    lambda: transcribe_audio("temp/dummy.wav"),
    "bağlanılamadı",
)
os.environ.pop("SONIOX_BASE_URL", None)

# 3) Anahtar eksik
os.environ["SONIOX_API_KEY"] = ""
expect_error(
    "Anahtar eksik -> yönlendirme mesajı",
    lambda: transcribe_audio("temp/dummy.wav"),
    "API anahtarı bulunamadı",
)

# 4) Placeholder anahtar
os.environ["SONIOX_API_KEY"] = "your-api-key-here"
expect_error(
    "Placeholder anahtar -> uyarı mesajı",
    lambda: transcribe_audio("temp/dummy.wav"),
    "henüz ayarlanmamış",
)

# 5) Var olmayan dosya
os.environ["SONIOX_API_KEY"] = "test"
expect_error(
    "Var olmayan dosya",
    lambda: transcribe_audio("temp/yok.wav"),
    "Dosya bulunamadı",
)

# 6) Desteklenmeyen uzantı
Path("temp/dummy.txt").write_text("x")
expect_error(
    "Desteklenmeyen uzantı",
    lambda: transcribe_audio("temp/dummy.txt"),
    "Desteklenmeyen dosya türü",
)
Path("temp/dummy.txt").unlink()

# 7) Boş dosya
Path("temp/empty.wav").write_bytes(b"")
expect_error(
    "Boş dosya",
    lambda: transcribe_audio("temp/empty.wav"),
    "Dosya boş",
)
Path("temp/empty.wav").unlink()

# --- Biçimlendirme modülü (ağsız) ---
# Gerçekçi Soniox token modeli: ilk token boşluksuz başlar; sonraki her kelimenin
# başlangıcı, token metninin BAŞINDAKİ boşlukla işaretlenir (gerçek API verisiyle
# doğrulandı — bkz. temp/jfk_result.json).
tokens = [
    {"text": "Merhaba,", "start_ms": 3000, "end_ms": 3600, "speaker": "1"},
    {"text": " hoş", "start_ms": 3700, "end_ms": 4000, "speaker": "1"},
    {"text": " geldiniz.", "start_ms": 4100, "end_ms": 4500, "speaker": "1"},
    {"text": "Teşekkürler.", "start_ms": 9000, "end_ms": 9600, "speaker": "2"},
]
turns = group_tokens_by_speaker(tokens)
assert len(turns) == 2, f"2 tur bekleniyordu, {len(turns)} geldi"
assert turns[0]["speaker"] == "1" and turns[1]["speaker"] == "2"
fmt = format_transcript({"id": "x", "text": "t", "tokens": tokens}, "test_kaydi")
assert fmt.txt.startswith("Konuşmacı 1 [00:00:03]:")
assert "Konuşmacı 2 [00:00:09]:" in fmt.txt
assert fmt.srt.startswith("1\n00:00:03,000 --> 00:00:04,500")
assert "Merhaba, hoş geldiniz." in fmt.txt  # noktalama öncesi boşluk temizlendi
assert "Merhaba,hoş" not in fmt.txt  # kelimeler birbirine yapışmamalı
assert format_timestamp(3661000) == "01:01:01"
assert format_srt_timestamp(3661234) == "01:01:01,234"
assert sanitize_filename("Toplantı_Kaydı (1).mp4") == "toplanti_kaydi__1__mp4"
print("OK   : Biçimlendirme modülü (turlar, TXT/SRT, zaman damgaları, dosya adı)")

# Parça (fragment) regresyonu — kullanıcının bildirdiği hata:
# 'Mer hab a, Ek in Ot omas yon kap ı sistem ler i.' -> 'Merhaba, Ekin Otomasyon kapı sistemleri.'
fragments = [
    # Aynı kelimenin devam parçaları boşluksuz gelir; YENİ kelimenin başlangıcı
    # token metninin başındaki boşlukla işaretlenir (gerçek API modeli).
    {"text": "Mer", "start_ms": 100, "end_ms": 200, "speaker": "1"},
    {"text": "hab", "start_ms": 250, "end_ms": 350, "speaker": "1"},
    {"text": "a,", "start_ms": 350, "end_ms": 400, "speaker": "1"},
    {"text": " Ek", "start_ms": 500, "end_ms": 600, "speaker": "1"},
    {"text": "in", "start_ms": 600, "end_ms": 700, "speaker": "1"},
    {"text": " Ot", "start_ms": 800, "end_ms": 900, "speaker": "1"},
    {"text": "omas", "start_ms": 900, "end_ms": 1000, "speaker": "1"},
    {"text": "yon", "start_ms": 1000, "end_ms": 1100, "speaker": "1"},
    {"text": " kap", "start_ms": 1200, "end_ms": 1300, "speaker": "1"},
    {"text": "ı", "start_ms": 1300, "end_ms": 1400, "speaker": "1"},
    {"text": " sistem", "start_ms": 1500, "end_ms": 1700, "speaker": "1"},
    {"text": "leri.", "start_ms": 1700, "end_ms": 1900, "speaker": "1"},
]
fmt_frag = format_transcript({"id": "x", "tokens": fragments}, "frag")
assert "Merhaba, Ekin Otomasyon kapı sistemleri." in fmt_frag.txt
assert "Mer hab" not in fmt_frag.txt  # bölük parçalar artık olmamalı
assert "kap ı" not in fmt_frag.txt  # 'ı' harfi kelimeye bitişmeli
print("OK   : Parça (fragment) token'lar doğru birleşiyor, Türkçe karakterler korunuyor")

# Token'sız yanıtta doğrudan üst seviye `text` alanı kullanılmalı (kullanıcı kararı)
fmt_fallback = format_transcript({"id": "x", "text": "Token yok, tam metin."}, "fallback")
assert fmt_fallback.turns[0]["speaker"] == "1"
assert "Token yok, tam metin." in fmt_fallback.txt
print("OK   : Token'sız yanıtta doğrudan `text` alanı kullanılıyor")

# Gerçek veri regresyonu: birleştirme, Soniox'un kendi üst seviye metnini
# birebir yeniden üretmeli (temp/jfk_result.json varsa).
jfk_path = Path("temp/jfk_result.json")
if jfk_path.exists():
    import json as _json

    from src.transcription_service import _join_token_texts

    real = _json.loads(jfk_path.read_text(encoding="utf-8"))
    joined = _join_token_texts(real["tokens"])
    assert joined == real["text"], (
        f"Birleştirme Soniox'un kendi metniyle uyuşmuyor:\n{joined!r}\nvs\n{real['text']!r}"
    )
    print("OK   : Gerçek JFK verisinde birleştirme, üst seviye `text` ile birebir aynı")
else:
    print("ATLA : temp/jfk_result.json yok — gerçek veri regresyonu çalıştırılmadı")

Path("temp/dummy.wav").unlink()

if failures:
    print(f"\n{failures} test başarısız")
    sys.exit(1)
print("\nTüm testler başarılı")
