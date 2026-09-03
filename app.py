"""Zoom Türkçe Transkripsiyon — Streamlit arayüzü.

Çalıştırma: streamlit run app.py
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

# Uygulama hangi dizinden başlatılırsa başlatılsın src/ paketinin
# bulunmasını garanti eder (ModuleNotFoundError: No module named 'src')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from dotenv import load_dotenv

from src.soniox_client import TranscriptionError, transcribe_audio
from src.transcription_service import format_transcript, write_output_files
from src.utils import format_elapsed, sanitize_filename

st.set_page_config(page_title="Zoom Türkçe Transkripsiyon", page_icon="🎙️", layout="wide")

load_dotenv()

TEMP_DIR = Path("temp")
OUTPUT_DIR = Path("output")
SUPPORTED_TYPES = ["mp4", "m4a", "mp3", "wav", "flac"]
SUPPORTED_EXTENSIONS = {f".{t}" for t in SUPPORTED_TYPES}
LANGUAGES = {"Türkçe": "tr", "İngilizce": "en"}


def _cleanup_dir(directory: Path) -> None:
    """Klasörü oluşturur ve içindeki eski dosyaları temizler."""
    directory.mkdir(exist_ok=True)
    for file in directory.glob("*"):
        try:
            file.unlink()
        except OSError:
            pass


def _sweep_stale_files(directory: Path, max_age_s: int = 3600) -> None:
    """Klasörü oluşturur, yalnızca belirtilen yaştan eski dosyaları siler.

    TEMP_DIR için yaş eşiği önemlidir: bir sekme transkripsiyon işlerken
    başka bir sekmenin rerun'ı taze yükleme dosyasını silmesin.
    """
    directory.mkdir(exist_ok=True)
    now = time.time()
    for file in directory.glob("*"):
        try:
            if file.is_file() and now - file.stat().st_mtime > max_age_s:
                file.unlink()
        except OSError:
            pass


# Her çalıştırmada geçici klasörlerdeki kalıntıları temizle
_sweep_stale_files(TEMP_DIR)
_cleanup_dir(OUTPUT_DIR)


def _run_transcription(uploaded_file, language: str) -> None:
    """Dosyayı temp/ altına kaydeder, transkripsiyonu çalıştırır, sonucu saklar."""
    suffix = Path(uploaded_file.name).suffix.lower()
    temp_path = TEMP_DIR / f"{uuid.uuid4().hex}{suffix}"
    base_name = sanitize_filename(Path(uploaded_file.name).stem)
    temp_path.write_bytes(uploaded_file.getbuffer())

    status = st.status(
        "Dosya yükleniyor ve transkripsiyon başlatılıyor...", expanded=True
    )
    try:
        def progress(elapsed: float, job_status: str) -> None:
            status.update(
                label=f"Transkripsiyon sürüyor... {format_elapsed(elapsed)} "
                f"(durum: {job_status})"
            )

        result = transcribe_audio(
            str(temp_path),
            language=language,
            original_filename=uploaded_file.name,
            progress_callback=progress,
        )

        status.update(label="Sonuç biçimlendiriliyor...", state="running")
        fmt = format_transcript(result, base_name)
        write_output_files(fmt, str(OUTPUT_DIR))

        st.session_state["result"] = fmt
        status.update(label="Transkripsiyon tamamlandı!", state="complete", expanded=False)
    except TranscriptionError as exc:
        status.update(label="Transkripsiyon başarısız oldu", state="error", expanded=False)
        st.error(str(exc))
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


# --- Arayüz ---

st.title("Zoom Türkçe Transkripsiyon")
st.markdown(
    "Zoom toplantı kayıtlarınızı yükleyin; saniyeler içinde **konuşmacı bazında "
    "etiketlenmiş**, zaman damgalı profesyonel transkripsiyon alın. Sonuçları "
    "TXT veya SRT (altyazı) olarak indirebilirsiniz."
)

with st.sidebar:
    st.subheader("Ayarlar")
    language_label = st.radio("Konuşma dili", list(LANGUAGES.keys()), index=0)
    st.caption("Konuşmacılar gelişmiş yapay zeka ile otomatik olarak algılanır.")
    st.divider()
    st.markdown(
        "**Desteklenen formatlar:** MP4, M4A, MP3, WAV, FLAC\n\n"
        "**Sınırlar:** 5 saate kadar kayıt (varsayılan 200 MB yükleme sınırı)."
    )

uploaded_file = st.file_uploader("Zoom kaydınızı yükleyin", type=SUPPORTED_TYPES)

if st.button("Transkripsiyonu Başlat", type="primary"):
    if uploaded_file is None:
        st.error("Lütfen önce bir dosya yükleyin.")
    elif Path(uploaded_file.name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        st.error(
            "Desteklenmeyen dosya türü. Lütfen MP4, M4A, MP3, WAV veya FLAC "
            "formatında bir dosya yükleyin."
        )
    elif uploaded_file.size == 0:
        st.error("Yüklenen dosya boş. Lütfen geçerli bir kayıt yükleyin.")
    else:
        st.session_state.pop("result", None)
        _run_transcription(uploaded_file, LANGUAGES[language_label])

# --- Sonuç gösterimi (session_state'ten; yeniden çalıştırmalarda korunur) ---

fmt = st.session_state.get("result")
if fmt is not None:
    st.success("Transkripsiyon tamamlandı!")

    st.subheader("Konuşmacı Bazında Metin")
    if fmt.markdown:
        st.markdown(fmt.markdown)
    else:
        st.warning("Transkripsiyon sonucu boş döndü. Lütfen farklı bir kayıt deneyin.")

    with st.expander("Ham Sonuç (JSON)"):
        st.json(fmt.raw)

    st.subheader("İndir")
    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "TXT İndir", data=fmt.txt, file_name=f"{fmt.base_name}.txt", mime="text/plain"
    )
    col2.download_button(
        "SRT (Altyazı) İndir",
        data=fmt.srt,
        file_name=f"{fmt.base_name}.srt",
        mime="application/x-subrip",
    )
    col3.download_button(
        "JSON İndir",
        data=json.dumps(fmt.raw, ensure_ascii=False, indent=2),
        file_name=f"{fmt.base_name}.json",
        mime="application/json",
    )
