# CLAUDE.md - Soniox Zoom Transkripsiyon Servisi

## 🎯 Proje Vizyonu (Vision)
Zoom toplantılarının Türkçe transkripsiyonunda yaşanan doğruluk sorunlarını **%98.75 (WER %1.25)** seviyesine çıkaran, bulut tabanlı bir web servisi geliştiriyoruz. Bu servis, müşterilerin Zoom'dan indirdikleri ses/video dosyalarını yükleyip, saniyeler içinde profesyonel, konuşmacı bazında etiketlenmiş transkripsiyon metinleri almasını sağlar.

## 👤 Proje Ekibi ve Rolleri
- **Mimari Yönetici (İnsan - Siz):** Stratejiyi belirler, kalite kontrolünü yapar, müşteri ile iletişimi sağlar.
- **Operasyonel Sunucu (İnsan - Siz):** Sunucu altyapısı, deployment, bakım ve müşteri desteğinden sorumludur.
- **Claude Code (AI Mühendis):** Tüm kodları yazar, test eder, hataları ayıklar ve nihai ürünü teslim eder.

## 🏗️ Sistem Mimarisi (Architecture)
Kullanıcı (Müşteri)
│
▼ (Zoom'dan indirilen MP4/M4A/MP3 dosyasını yükler)
┌──────────────────────────────────────────────────────────┐
│ Web Arayüzü (Streamlit) │
│ - Dosya Yükleme (Drag & Drop) │
│ - Dil Seçimi (Türkçe / İngilizce) │
│ - Konuşmacı Sayısı (Diyarizasyon) Ayarları │
│ - "Transkripsiyonu Başlat" Butonu │
│ - İlerleme Çubuğu / Spinner │
│ - Sonucu Görüntüleme (Metin + Zaman Damgaları) │
│ - İndirme Butonları (TXT, SRT altyazı, JSON) │
└──────────────────────────────────────────────────────────┘
│
▼ (API Anahtarı ile güvenli bağlantı)
┌──────────────────────────────────────────────────────────┐
│ Soniox Cloud API │
│ - Dosyayı alır, Türkçe konuşma tanıma yapar. │
│ - Konuşmacıları ayırt eder (Diyarizasyon). │
│ - Zaman damgalı ve doğruluk oranı yüksek JSON döndürür.│
└──────────────────────────────────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────────┐
│ Çıktı İşleme Katmanı │
│ - Gelen JSON'u okunabilir metne çevirir. │
│ - Konuşmacı etiketlerini ekler (Konuşmacı 1, 2...). │
│ - SRT (altyazı) formatına dönüştürür. │


## 📁 Proje Dizini Yapısı (Zorunlu)

/soniox_transcription_service
│
├── app.py # Streamlit ana uygulama dosyası
├── requirements.txt # Bağımlılıklar (streamlit, requests, python-dotenv)
├── .env # API anahtarları (GİZLİ, .gitignore'a ekle)
├── .gitignore # .env, pycache, temp/ klasörlerini gizle
│
├── src/ # Kaynak kodlar
│ ├── init.py
│ ├── soniox_client.py # Soniox API ile iletişim kuran modül
│ ├── transcription_service.py # İş mantığı, dosya yönetimi, format dönüşümleri
│ └── utils.py # Yardımcı fonksiyonlar (zaman damgası formatlama vb.)
│
├── temp/ # Geçici yükleme ve işleme dosyaları (otomatik temizlenir)
│
├── output/ # Kullanıcının indireceği dosyaların geçici üretim yeri
│
├── docker-compose.yml # (Opsiyonel) Docker ile hızlı kurulum için
└── README.md # Kurulum, kullanım ve müşteri teklif metni


## ⚙️ Teknik Gereksinimler (Tech Stack)
- **Frontend & Backend:** Python 3.10+, Streamlit (Web UI)
- **STT Motoru:** Soniox API (Türkçe için en yüksek doğruluk)
- **Kütüphaneler:** `streamlit`, `requests`, `python-dotenv`, `ffmpeg-python` (ses/video işleme için)
- **Deployment:** Streamlit Community Cloud (demo için) veya Docker + VPS (üretim için)
- **API Standardı:** RESTful (Soniox Async API)

## 🚀 Nihai Teslimat Kriterleri (Definition of Done)
1. `app.py` çalıştırıldığında yerelde `http://localhost:8501` adresinde arayüz açılmalı.
2. Kullanıcı bir Zoom kaydını (MP4, M4A, MP3) yükleyebilmeli.
3. "Transkripsiyonu Başlat" butonuna tıklanınca, dosya Soniox'a gönderilmeli, işlem tamamlanana kadar bekleme ekranı gösterilmeli.
4. Sonuç geldiğinde, metin konuşmacı bazında ayrıştırılmış olarak ekranda gösterilmeli.
5. Kullanıcı sonucu **TXT (düz metin)** ve **SRT (altyazı)** formatlarında indirebilmeli.
6. Hata durumlarında (API hatası, dosya bozuk vb.) kullanıcıyı bilgilendiren Türkçe hata mesajları gösterilmeli.
7. (Opsiyonel) Zoom SDK ile entegrasyon için altyapı hazırlanmalı.

## 💰 İş Modeli ve Müşteri Teklifi
- **Kurulum Ücreti (Tek seferlik):** Sistemin müşterinin kendi sunucusuna kurulumu, testi ve devreye alınması.
- **Aylık Bakım Ücreti:** Sistemin çalışır durumda tutulması, güncellemeler, 7/24 destek ve Soniox API kullanım bedelinin yönetilmesi. (Soniox API ücreti + kar marjı olarak yansıtılır).
- **Demo Sunumu:** Müşteriye önce bu sistemin bir demosu gösterilir, beğenirse kuruluma geçilir.

