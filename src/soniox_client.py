"""Soniox Async REST API istemcisi.

Akış:
  1. Dosya yükle:   POST /v1/files                      -> file_id
  2. İş oluştur:    POST /v1/transcriptions             -> job id + status
  3. Durum sorgula: GET  /v1/transcriptions/{id}        -> queued|processing|completed|error
  4. Sonuç al:      GET  /v1/transcriptions/{id}/transcript -> {id, text, tokens}

Tüm hatalar, kullanıcıya gösterilebilecek Türkçe mesaj taşıyan
TranscriptionError olarak yükseltilir. Modül Streamlit'e bağımlı değildir;
tek başına (python -c) test edilebilir.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

# --- API ayarları (ortam değişkenleriyle geçersiz kılınabilir) ---

DEFAULT_BASE_URL = "https://api.soniox.com/v1"
DEFAULT_MODEL = os.getenv("SONIOX_MODEL", "stt-async-v5")
DEFAULT_POLL_INTERVAL_S = 3.0
DEFAULT_MAX_WAIT_S = float(os.getenv("SONIOX_MAX_WAIT_SECONDS", "1800"))  # 30 dk

SUPPORTED_EXTENSIONS = {".mp4", ".m4a", ".mp3", ".wav", ".flac"}

# Ağa gitmeden reddedilen anahtar değerleri. "test" bilinçli olarak burada
# DEĞİL: kullanıcının istediği test senaryosu (anahtar "test" iken) gerçek
# 401 cevabını görmeli, böylece HTTP hata eşlemesi de test edilmiş olur.
PLACEHOLDER_API_KEYS = {"", "your-api-key-here"}

# (bağlantı, okuma) saniye cinsinden zaman aşımları
TIMEOUT_UPLOAD = (10, 600)  # büyük dosyalar için okuma aşımı geniş
TIMEOUT_SHORT = (10, 30)
TIMEOUT_GET = (10, 60)


def get_base_url() -> str:
    """Temel URL'yi döndürür.

    SONIOX_BASE_URL bir test kancasıdır: bağlantı hatası senaryolarının gerçek
    API'ye dokunmadan çalıştırılmasını sağlar. Değer istek anında okunur.
    """
    return os.getenv("SONIOX_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


class TranscriptionError(Exception):
    """Kullanıcıya gösterilecek Türkçe hata mesajı taşıyan istisna."""

    def __init__(
        self,
        message: str,
        error_type: str | None = None,
        status_code: int | None = None,
        request_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.request_id = request_id

    def __str__(self) -> str:
        # app.py tarafında st.error(str(e)) yeterli olur
        return self.message


def get_api_key() -> str:
    """.env dosyasından SONIOX_API_KEY değerini okur; eksikse Türkçe hata."""
    load_dotenv()
    api_key = (os.getenv("SONIOX_API_KEY") or "").strip().strip('"').strip("'")
    if not api_key:
        raise TranscriptionError(
            "SONIOX_API_KEY bulunamadı. Lütfen .env dosyasına API anahtarınızı ekleyin "
            "(bkz. .env.example).",
            error_type="missing_api_key",
        )
    if api_key.lower() in PLACEHOLDER_API_KEYS:
        raise TranscriptionError(
            "SONIOX_API_KEY henüz ayarlanmamış. Lütfen .env dosyasındaki değeri gerçek "
            "API anahtarınızla değiştirin.",
            error_type="placeholder_api_key",
        )
    return api_key


def _map_error(
    status_code: int, error_type: str | None, message: str | None, is_upload: bool = False
) -> str:
    """HTTP durum kodunu Türkçe kullanıcı mesajına eşler."""
    if status_code == 400:
        if is_upload:
            return (
                "Yüklenen dosya geçersiz veya desteklenmeyen bir formatta. Lütfen MP4, M4A, "
                "MP3, WAV veya FLAC formatında bir dosya yükleyin."
            )
        return f"İstek geçersiz: {message or 'bilinmeyen neden'}"
    if status_code == 401:
        return (
            "API anahtarı geçersiz. Lütfen .env dosyanızdaki SONIOX_API_KEY değerini "
            "kontrol edin."
        )
    if status_code == 402:
        return (
            "Soniox hesabınızın bakiyesi yetersiz veya aylık kullanım limiti aşılmış. "
            "Lütfen app.soniox.com adresinden bakiye yükleyin veya otomatik ödemeyi "
            "etkinleştirin."
        )
    if status_code == 404:
        return "Transkripsiyon sonucu bulunamadı. Lütfen tekrar deneyin."
    if status_code == 409:
        return "Transkripsiyon henüz tamamlanmadı. Lütfen kısa süre sonra tekrar deneyin."
    if status_code == 413:
        return "Dosya çok büyük. Lütfen daha küçük bir dosya yükleyin (maks. 5 saatlik kayıt)."
    if status_code == 429:
        return "Çok fazla istek gönderildi. Lütfen bir dakika bekleyip tekrar deneyin."
    if status_code >= 500:
        return "Soniox sunucusunda bir hata oluştu. Lütfen daha sonra tekrar deneyin."
    if message:
        return f"İstek geçersiz: {message}"
    return f"Beklenmeyen bir hata oluştu (HTTP {status_code}). Lütfen tekrar deneyin."


def _raise_for_api_error(resp: requests.Response, is_upload: bool = False) -> None:
    """API hata cevabını ayrıştırıp TranscriptionError yükseltir."""
    error_type = None
    message = None
    request_id = None
    try:
        body = resp.json()
        if isinstance(body, dict):
            error_type = body.get("error_type")
            message = body.get("message")
            request_id = body.get("request_id")
    except ValueError:
        pass  # JSON olmayan cevap (proxy/HTML): durum koduna göre eşle
    raise TranscriptionError(
        _map_error(resp.status_code, error_type, message, is_upload=is_upload),
        error_type=error_type,
        status_code=resp.status_code,
        request_id=request_id,
    )


def _request(method: str, path: str, api_key: str, **kwargs) -> requests.Response:
    """Tek noktadan istek atar; ağ hatalarını Türkçe mesaja çevirir."""
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {api_key}"
    try:
        return requests.request(method, f"{get_base_url()}{path}", headers=headers, **kwargs)
    except requests.ConnectionError as exc:
        raise TranscriptionError(
            "Soniox sunucusuna bağlanılamadı. İnternet bağlantınızı kontrol edin ve "
            "tekrar deneyin.",
            error_type="connection_error",
        ) from exc
    except requests.Timeout as exc:
        raise TranscriptionError(
            "Soniox sunucusuna istek zaman aşımına uğradı. Lütfen tekrar deneyin.",
            error_type="timeout",
        ) from exc
    except requests.RequestException as exc:
        raise TranscriptionError(
            "Soniox API ile iletişim kurulamadı. Lütfen tekrar deneyin.",
            error_type="request_error",
        ) from exc


def _upload_file(path: Path, filename: str, api_key: str) -> str:
    """Dosyayı POST /files ile yükler, file_id döndürür."""
    with path.open("rb") as fh:
        resp = _request(
            "POST",
            "/files",
            api_key,
            # Gerçek dosya adını multipart'ta göndermek sunucuda korunmasını sağlar
            files={"file": (filename, fh)},
            data={"client_reference_id": f"zoomspeak-{uuid.uuid4().hex[:8]}"},
            timeout=TIMEOUT_UPLOAD,
        )
    if resp.status_code != 201:
        _raise_for_api_error(resp, is_upload=True)
    return resp.json()["id"]


def _create_job(file_id: str, language: str, api_key: str) -> str:
    """POST /transcriptions ile async transkripsiyon işi oluşturur, job id döndürür.

    Not: Soniox API'sinde konuşmacı sayısı parametresi yoktur. Diyarizasyon
    enable_speaker_diarization ile açılır ve konuşmacılar otomatik algılanır.
    """
    body = {
        "model": DEFAULT_MODEL,
        "file_id": file_id,
        "language_hints": [language],
        "enable_speaker_diarization": True,
    }
    resp = _request("POST", "/transcriptions", api_key, json=body, timeout=TIMEOUT_SHORT)
    if resp.status_code != 201:
        _raise_for_api_error(resp)
    return resp.json()["id"]


_BALANCE_ERROR_TYPES = {
    "organization_balance_exhausted",
    "organization_monthly_budget_exhausted",
    "project_monthly_budget_exhausted",
}


def _job_error_message(job: dict) -> str:
    """İş hatasını Türkçe kullanıcı mesajına çevirir (bakiye hataları öncelikli).

    Bakiye hatası HTTP 200 + status="error" olarak da gelebilir; bu durumda
    API'nin İngilizce mesajı yerine yönlendirici Türkçe mesaj gösterilir.
    """
    error_type = job.get("error_type") or ""
    error_message = job.get("error_message") or ""
    if error_type in _BALANCE_ERROR_TYPES or "balance" in error_message.lower():
        return (
            "Soniox hesabınızın bakiyesi yetersiz veya aylık kullanım limiti aşılmış. "
            "Lütfen app.soniox.com adresinden bakiye yükleyin veya otomatik ödemeyi "
            "etkinleştirin."
        )
    return f"Transkripsiyon başarısız oldu: {error_message or error_type or 'bilinmeyen neden'}"


def _poll_job(
    job_id: str,
    api_key: str,
    poll_interval_s: float,
    max_wait_s: float,
    progress_callback,
) -> dict:
    """İş bitene kadar durumu sorgular; tamamlanan işin bilgisini döndürür."""
    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        if elapsed > max_wait_s:
            raise TranscriptionError(
                f"Transkripsiyon zaman aşımına uğradı ({int(max_wait_s // 60)} dakika). "
                "Lütfen tekrar deneyin.",
                error_type="client_timeout",
            )
        resp = _request("GET", f"/transcriptions/{job_id}", api_key, timeout=TIMEOUT_SHORT)
        if resp.status_code != 200:
            _raise_for_api_error(resp)
        job = resp.json()
        status = job.get("status")
        if progress_callback:
            progress_callback(elapsed, status)
        if status == "completed":
            return job
        if status == "error":
            raise TranscriptionError(
                _job_error_message(job),
                error_type=job.get("error_type"),
                request_id=job.get("request_id"),
            )
        time.sleep(poll_interval_s)


def _fetch_transcript(job_id: str, api_key: str) -> dict:
    """GET /transcriptions/{id}/transcript ile sonucu alır."""
    resp = _request("GET", f"/transcriptions/{job_id}/transcript", api_key, timeout=TIMEOUT_GET)
    if resp.status_code != 200:
        _raise_for_api_error(resp)
    return resp.json()


def transcribe_audio(
    file_path,
    language: str = "tr",
    speakers: int = 2,
    original_filename: str | None = None,
    progress_callback=None,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    max_wait_s: float = DEFAULT_MAX_WAIT_S,
) -> dict:
    """Ses/video dosyasını Soniox'a gönderir ve transkripsiyon sonucunu döndürür.

    Dönen JSON: {"id": ..., "text": ..., "tokens": [{text, start_ms, end_ms,
    confidence, speaker?}]}

    `speakers` yalnızca imza uyumluluğu için kabul edilir; API'ye GÖNDERİLMEZ
    (Soniox konuşmacı sayısını otomatik algılar). `progress_callback` her
    poll turunda (elapsed_seconds, job_status) ile çağrılır.
    """
    path = Path(file_path)
    if not path.exists():
        raise TranscriptionError(f"Dosya bulunamadı: {path}", error_type="file_not_found")
    if path.stat().st_size == 0:
        raise TranscriptionError(
            "Dosya boş. Lütfen geçerli bir ses/video dosyası yükleyin.",
            error_type="empty_file",
        )
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise TranscriptionError(
            f"Desteklenmeyen dosya türü: {path.suffix}. Desteklenenler: mp4, m4a, mp3, wav, flac.",
            error_type="unsupported_type",
        )

    api_key = get_api_key()
    filename = original_filename or path.name
    file_id = _upload_file(path, filename, api_key)
    job_id = _create_job(file_id, language, api_key)
    _poll_job(job_id, api_key, poll_interval_s, max_wait_s, progress_callback)
    return _fetch_transcript(job_id, api_key)
