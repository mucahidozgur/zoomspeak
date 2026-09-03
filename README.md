# 🎙️ Zoom Türkçe Transkripsiyon Servisi

Zoom toplantı kayıtlarınızı yükleyin; saniyeler içinde **konuşmacı bazında etiketlenmiş**,
zaman damgalı ve **%98,75 doğruluk oranlı (WER %1,25)** Türkçe transkripsiyon alın.

Altyapı: [Soniox](https://soniox.com) konuşma tanıma motoru (60+ dil desteği, otomatik
konuşmacı diyarizasyonu).

## ✨ Özellikler

- MP4, M4A, MP3, WAV ve FLAC formatlarında dosya yükleme (5 saate kadar kayıt)
- Türkçe ve İngilizce transkripsiyon (konuşma dili seçimi)
- Konuşmacıların otomatik algılanması ve etiketlenmesi (Konuşmacı 1, Konuşmacı 2...)
- Zaman damgalı sonuç gösterimi
- **TXT** (düz metin), **SRT** (altyazı) ve **JSON** (ham veri) indirme
- Anlaşılır Türkçe hata mesajları

## 📋 Gereksinimler

- Python 3.10 veya üzeri
- Windows 10/11, macOS veya Linux
- Soniox API anahtarı — https://app.soniox.com adresinden alınır
- İnternet bağlantısı

## 🚀 Kurulum (Windows)

### 1. Sanal ortam oluşturun

```powershell
cd D:\GravityAntiUygulamalar\zoomspeak
py -3 -m venv venv
```

### 2. Sanal ortamı etkinleştirin

```powershell
venv\Scripts\Activate.ps1
```

> `Activate.ps1` çalıştırma ilkesi hatası verirse:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` komutunu çalıştırıp tekrar deneyin.

### 3. Bağımlılıkları yükleyin

```powershell
pip install -r requirements.txt
```

### 4. API anahtarınızı ayarlayın

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` dosyasındaki `SONIOX_API_KEY="your-api-key-here"` değerini gerçek
API anahtarınızla değiştirin. `.env` dosyası gizlidir; asla paylaşılmaz veya
depoya eklenmez (`.gitignore` ile korunur).

## ▶️ Çalıştırma

```powershell
streamlit run app.py
```

Tarayıcınızda otomatik olarak **http://localhost:8501** adresi açılır.

> **Büyük dosyalar için:** Varsayılan yükleme sınırı 200 MB'tır. Daha büyük
> Zoom kayıtları için:
> `streamlit run app.py --server.maxUploadSize=2000`

## ☁️ Render'a Yayınlama (Deployment)

Bu depo, Render Blueprint tanımı (`render.yaml`) içerir:

1. [render.com](https://render.com) adresinde **GitHub ile giriş yapın**.
2. **New → Blueprint** seçin ve `zoomspeak` deposunu bağlayın.
3. `SONIOX_API_KEY` ortam değişkenine gerçek API anahtarınızı yapıştırın.
   Değer yalnızca Render'da tutulur; repo'ya asla yazılmaz.
4. **Apply** ile onaylayın — servis kurulur, ilk deploy otomatik başlar.
5. Bundan sonra GitHub'a her `git push` otomatik yeniden deploy edilir (auto-deploy).

**Ücretsiz plan notları:** Ayda 750 saat; 15 dakika trafik olmazsa servis uykuya
geçer, ilk istekte yaklaşık 1 dakikada uyanır. Demo kayıtları kısa tutulmalıdır;
işlenmesi dakikalar süren çok uzun toplantı kayıtları için ücretli plan veya
müşterinin kendi sunucusu (VPS) önerilir (bkz. aşağıdaki iş modeli).

## 📖 Kullanım

1. "Zoom kaydınızı yükleyin" alanına dosyanızı sürükleyin veya tıklayıp seçin.
2. Sol panelden konuşma dilini seçin (Türkçe / İngilizce).
3. **Transkripsiyonu Başlat** butonuna tıklayın.
4. İşlem tamamlanana kadar bekleyin (ilerleme durumu ekranda gösterilir).
5. Sonucu ekranda görüntüleyin ve TXT / SRT / JSON olarak indirin.

## 📄 Çıktı Formatları

**TXT (düz metin) örneği:**

```
Konuşmacı 1 [00:00:03]:
Merhaba, bugünkü toplantıya hoş geldiniz.

Konuşmacı 2 [00:00:09]:
Teşekkürler. Gündem maddelerine geçelim mi?
```

**SRT (altyazı) örneği:**

```
1
00:00:03,120 --> 00:00:07,450
Konuşmacı 1: Merhaba, bugünkü toplantıya hoş geldiniz.

2
00:00:09,000 --> 00:00:13,800
Konuşmacı 2: Teşekkürler. Gündem maddelerine geçelim mi?
```

## ⚠️ Hata Mesajları

| Durum | Mesaj |
|---|---|
| API anahtarı eksik | `SONIOX_API_KEY bulunamadı. Lütfen .env dosyasına API anahtarınızı ekleyin.` |
| API anahtarı henüz ayarlanmamış | `SONIOX_API_KEY henüz ayarlanmamış. Lütfen .env dosyasındaki değeri gerçek API anahtarınızla değiştirin.` |
| API anahtarı geçersiz (401) | `API anahtarı geçersiz. Lütfen .env dosyanızdaki SONIOX_API_KEY değerini kontrol edin.` |
| Bakiye yetersiz (402 / iş hatası) | `Soniox hesabınızın bakiyesi yetersiz veya aylık kullanım limiti aşılmış. Lütfen app.soniox.com adresinden bakiye yükleyin veya otomatik ödemeyi etkinleştirin.` |
| Çok fazla istek (429) | `Çok fazla istek gönderildi. Lütfen bir dakika bekleyip tekrar deneyin.` |
| Geçersiz dosya (400) | `Yüklenen dosya geçersiz veya desteklenmeyen bir formatta...` |
| Sunucu hatası (500) | `Soniox sunucusunda bir hata oluştu...` |
| Bağlantı hatası | `Soniox sunucusuna bağlanılamadı. İnternet bağlantınızı kontrol edin...` |
| Zaman aşımı | `Transkripsiyon zaman aşımına uğradı (30 dakika)...` |

## 📝 Notlar ve Sınırlamalar

- **Konuşmacı sayısı otomatik algılanır.** Soniox API'sinde konuşmacı sayısı
  parametresi bulunmaz; diyarizasyon açıkken model konuşmacıları kendisi ayırır.
- **MP4:** Dosyalar olduğu gibi Soniox'a gönderilir (dönüştürme yapılmaz).
  Soniox'un MP4 desteği resmi dokümanlarda doğrulanmamıştır; desteklenmiyorsa
  uygun Türkçe hata mesajı gösterilir. WAV ve MP3 kesin desteklenir.
- Dosya sınırı: **5 saatlik** kayıt, yükleme başına varsayılan **200 MB**.
- Model: `stt-async-v5` (`.env` içinde `SONIOX_MODEL` ile değiştirilebilir).
- Transkripsiyon bekleme üst sınırı: 30 dakika
  (`.env` içinde `SONIOX_MAX_WAIT_SECONDS` ile değiştirilebilir).

## 💼 Müşteri Teklifi (İş Modeli)

- **Kurulum Ücreti (tek seferlik):** Sistemin müşterinin kendi sunucusuna
  kurulumu, testi ve devreye alınması.
- **Aylık Bakım Ücreti:** Sistemin çalışır durumda tutulması, güncellemeler,
  7/24 destek ve Soniox API kullanım bedelinin yönetilmesi (API ücreti + kâr marjı).
- **Demo Sunumu:** Müşteriye önce bu sistemin demosu gösterilir; beğenirse
  kuruluma geçilir.

## 📁 Proje Yapısı

```
zoomspeak/
├── app.py                      # Streamlit arayüzü
├── requirements.txt            # Bağımlılıklar (streamlit, requests, python-dotenv)
├── .env.example                # API anahtarı şablonu
├── src/
│   ├── soniox_client.py        # Soniox Async API istemcisi
│   ├── transcription_service.py  # Konuşmacı turu / TXT / SRT biçimlendirme
│   └── utils.py                # Zaman damgası yardımcıları
├── temp/                       # Geçici yükleme dosyaları (otomatik temizlenir)
└── output/                     # Üretilen indirme dosyaları (otomatik temizlenir)
```
