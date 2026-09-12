# ERA5-Land Web GIS

Web GIS interaktif dan modern untuk eksplorasi, visualisasi, dan analisis data hidrometeorologi **ERA5-Land** dari file NetCDF tanpa mengirim file mentah ke browser.

Dibangun dengan arsitektur **Python Flask + xarray/Dask** di backend, dan **Flask Jinja2 + Leaflet.js + Apache ECharts** di frontend.

---

## 📑 Daftar Isi
1. [Fitur Utama](#-fitur-utama)
2. [Struktur Project](#-struktur-project)
3. [Teknologi](#-teknologi)
4. [Dataset & Variabel](#-dataset--variabel)
5. [Instalasi & Menjalankan Aplikasi](#-instalasi--menjalankan-aplikasi)
6. [Dokumentasi API RESTful](#-dokumentasi-api-restful)
7. [Panduan Penggunaan Antarmuka](#-panduan-penggunaan-antarmuka)
8. [Arsitektur & Optimasi Kinerja](#-arsitektur--optimasi-kinerja)

---

## 🌟 Fitur Utama

- **Visualisasi Raster Dinamis**: Menampilkan grid layer ERA5-Land pada Leaflet map dengan rendering RGBA transparan otomatis (daratan berwarna sesuai variabel, lautan transparan).
- **Multi-Variabel Meteorologi & Hidrologi**: Mendukung 13 variabel utama (temperatur, titik embun, curah hujan, evaporasi potensial, limpasan air, tekanan permukaan, 4 lapisan kelembaban tanah, dan komponen angin).
- **Konversi Unit Otomatis**: Konversi temperatur dari Kelvin ke °C, presipitasi/evaporasi/runoff dari m ke mm, tekanan dari Pa ke hPa.
- **Agregasi Temporal**: Pilihan agregasi *Hourly* (per jam), *Daily* (harian), *Monthly* (bulanan), dan *Yearly* (tahunan) dengan logika sesuai karakteristik variabel (*mean* untuk suhu, *sum* untuk hujan).
- **Interactive Point Query**: Klik sembarang titik koordinat pada daratan peta untuk membaca nilai aktual dan memunculkan grafik **Time Series ECharts** interaktif.
- **Analisis Poligon Spasial**: Gambar poligon bebas pada peta untuk menghitung statistik spasial (min, max, mean, total, std, jumlah sel grid) dan time series rata-rata area penelitian.
- **Vektor Angin (Wind Vectors)**: Visualisasi panah arah dan kecepatan angin pada peta berdasarkan vektor $u_{10}$ dan $v_{10}$.
- **Batas Wilayah Administratif**: Overlay batas provinsi/kabupaten di kawasan Sumatera.
- **Time Series Player**: Tombol animasi *Play/Pause/Step* untuk memutar perkembangan cuaca/iklim per jam secara otomatis.
- **Kontrol Opacity & Tampilan**: Slider opacity 0-100%, toggle interpolasi halus (*bilinear*) vs grid tajam (*nearest-neighbor*), dan pilihan basemap (*OpenStreetMap* dan *ESRI World Imagery*).
- **Ekspor Data CSV**: Mengunduh seluruh time series titik ke file CSV siap olah.

---

## 📁 Struktur Project

Mengikuti panduan implementasi spesifikasi:

```text
project/
├── backend/
│   ├── app/
│   │   ├── __init__.py               # Flask app factory & routing Jinja2
│   │   ├── config.py                 # Konfigurasi variabel, skala warna, & chunking
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── variables.py          # Endpoint /api/variables & /api/health
│   │   │   ├── map.py                # Endpoint /api/map, /api/map/raster, /api/times, /api/wind
│   │   │   ├── timeseries.py         # Endpoint /api/timeseries (point query)
│   │   │   ├── statistics.py         # Endpoint /api/statistics & /api/statistics/polygon
│   │   │   └── download.py           # Endpoint /api/download (CSV export)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── netcdf_service.py     # Lazy loading NetCDF via xarray & dask
│   │   │   ├── raster_service.py     # Colormapping, PNG rendering & legend generator
│   │   │   └── statistics_service.py # Spatial & temporal statistics computation
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── units.py              # Konversi satuan (K->°C, m->mm, Pa->hPa)
│   ├── data/
│   │   └── ERA5-Land.nc              # Symlink / file dataset NetCDF
│   ├── requirements.txt              # Daftar dependensi Python
│   └── run.py                        # Entrypoint backend
│
├── app/
│   ├── templates/
│   │   ├── base.html                 # Template dasar Jinja2 (navbar, modal, CDN)
│   │   └── index.html                # Antarmuka utama Web GIS & ECharts
│   └── static/
│       ├── css/
│       │   └── app.css               # Styling dark mode modern responsif
│       ├── js/
│       │   ├── map.js                # Logika peta Leaflet, overlay, & drawing tool
│       │   └── dashboard.js          # Controller filter, ECharts chart, & time player
│       └── data/
│           └── sumatra_boundaries.geojson # Batas wilayah administratif
│
├── run.py                            # Launcher cepat dari root
└── README.md
```

---

## 🛠 Teknologi

### Backend
- **Python 3.11+**
- **Flask**: Web framework dan REST API.
- **Flask-CORS**: Mendukung request lintas origin jika diperlukan.
- **xarray & Dask**: Pembacaan lazy data multidimensional NetCDF dan pemrosesan chunking.
- **NumPy & Pandas**: Kalkulasi numerik dan manipulasi time-series.
- **rasterio & rioxarray**: Penanganan georeferensi spasial.
- **Pillow & Matplotlib**: Generasi gambar PNG transparan ber-colormap dan visualisasi legend.
- **Shapely**: Analisis spasial point-in-polygon untuk kalkulasi statistik poligon penelitian.

### Frontend
- **Flask Jinja2**: Server-side rendering (SSR) halaman web.
- **Leaflet.js**: Engine peta Web GIS interaktif.
- **Leaflet.draw**: Alat menggambar poligon dan kotak area penelitian pada peta.
- **Apache ECharts**: Grafik time-series interaktif dengan dataZoom, area gradient, dan tooltip dinamis.
- **Vanilla JavaScript (ES6+)**: Interaksi komponen tanpa framework SPA yang berat.
- **CSS3 Modern**: Tema gelap (*dark theme*) responsif dengan CSS grid & flexbox.

---

## 📊 Dataset & Variabel

File sumber data: `ERA5-Land.nc`
- **Cakupan Spasial**: Latitude $-2.7^\circ$ s.d. $6.2^\circ$, Longitude $93.7^\circ$ s.d. $102.3^\circ$ (Kawasan Sumatera Tengah & Utara).
- **Resolusi Spasial**: $0.1^\circ \times 0.1^\circ$ (Grid $90 \times 87$).
- **Cakupan Waktu**: 480 timestep per jam (11 November 2025 s.d. 30 November 2025).

| ID Variabel | Nama Variabel | Satuan NetCDF | Satuan Tampilan | Kategori | Agregasi |
|:---|:---|:---:|:---:|:---:|:---:|
| `t2m` | Temperature 2 metre | K | **°C** | Suhu | Mean |
| `d2m` | Dewpoint temperature 2m | K | **°C** | Suhu | Mean |
| `tp` | Total precipitation | m | **mm** | Presipitasi | Sum |
| `pev` | Potential evaporation | m | **mm** | Hidrologi | Sum |
| `ro` | Runoff | m | **mm** | Hidrologi | Sum |
| `sp` | Surface pressure | Pa | **hPa** | Tekanan | Mean |
| `swvl1` | Soil water volume layer 1 (0-7cm) | m³/m³ | **m³/m³** | Tanah | Mean |
| `swvl2` | Soil water volume layer 2 (7-28cm) | m³/m³ | **m³/m³** | Tanah | Mean |
| `swvl3` | Soil water volume layer 3 (28-100cm) | m³/m³ | **m³/m³** | Tanah | Mean |
| `swvl4` | Soil water volume layer 4 (100-289cm) | m³/m³ | **m³/m³** | Tanah | Mean |
| `u10` | 10 metre U wind component | m/s | **m/s** | Angin | Mean |
| `v10` | 10 metre V wind component | m/s | **m/s** | Angin | Mean |
| `wind_speed`| 10m Wind speed ($\sqrt{u^2 + v^2}$) | m/s | **m/s** | Angin | Mean |

---

## 🚀 Instalasi & Menjalankan Aplikasi

### 1. Aktifkan Virtual Environment
```bash
# Menggunakan venv yang sudah disiapkan
source .venv/bin/activate
```

Atau membuat venv baru:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Jalankan Server Web GIS
Dari direktori utama proyek:
```bash
python run.py
```
Atau dari direktori backend:
```bash
python backend/run.py
```

Buka browser Anda di:
👉 **`http://127.0.0.1:5000/`**

---

## 📡 Dokumentasi API RESTful

### 1. Health Check
`GET /api/health`
Mengembalikan status server, jangkauan waktu, batas latitude/longitude, dan daftar variabel yang tersedia.

### 2. Daftar Variabel
`GET /api/variables`
Mengembalikan metadata seluruh variabel beserta satuan asli dan satuan tampilan.

### 3. Daftar Waktu
`GET /api/times?from=2025-11-11&to=2025-11-20&step=1`
Parameter:
- `from` *(opsional)*: Waktu awal (ISO format)
- `to` *(opsional)*: Waktu akhir (ISO format)
- `step` *(opsional, default 1)*: Interval pelompatan data.

### 4. Metadata Layer Peta
`GET /api/map?variable=t2m&time=2025-11-11T12:00:00&aggregation=hourly&smooth=true`
Mengembalikan informasi batas spasial (`bounds`), URL raster PNG yang siap dimasukkan ke `L.imageOverlay`, skala min/max, dan stops gradien warna untuk legenda.

### 5. Stream Raster Overlay PNG
`GET /api/map/raster?variable=t2m&time=2025-11-11T12:00:00&smooth=true`
Menghasilkan gambar PNG beresolusi tinggi dengan transparansi alpha untuk koordinat laut/non-data.

### 6. Query Time Series Titik
`GET /api/timeseries?variable=t2m&lat=-0.947&lon=100.417&aggregation=hourly`
Parameter:
- `variable`: ID variabel (cth: `t2m`, `tp`, dll.)
- `lat`: Latitude lokasi
- `lon`: Longitude lokasi
- `aggregation`: `hourly`, `daily`, `monthly`, atau `yearly`.

### 7. Vektor Angin
`GET /api/wind?time=2025-11-11T12:00:00&stride=3`
Mengembalikan koordinat, kecepatan, dan arah derajat angin untuk rendering panah aliran angin.

### 8. Statistik Bounding Box
`GET /api/statistics?variable=tp&from=2025-11-11&to=2025-11-20`
Menghitung nilai min, max, rata-rata, standar deviasi, dan total akumulasi.

### 9. Analisis Spasial Poligon
`POST /api/statistics/polygon`
Body (JSON):
```json
{
  "variable": "t2m",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [100.0, -1.0],
        [101.0, -1.0],
        [101.0, 0.0],
        [100.0, 0.0],
        [100.0, -1.0]
      ]
    ]
  }
}
```
Mengembalikan statistik nilai di dalam poligon dan rangkaian waktu rata-rata poligon.

### 10. Ekspor CSV
`GET /api/download?variable=t2m&lat=-0.947&lon=100.417&aggregation=daily`
Mengunduh time-series dalam format file `.csv`.

---

## 🖥 Panduan Penggunaan Antarmuka

1. **Memilih Variabel & Tanggal**:
   Gunakan dropdown di panel samping kiri untuk memilih parameter hidrometeorologi, tanggal, jam, dan tingkat agregasi. Klik tombol **"Perbarui Visualisasi"** untuk memuat peta.
2. **Animasi Perjalanan Waktu**:
   Tekan tombol **Play** pada widget *Time Series Player* di sidebar untuk memutar dinamika variabel secara otomatis dari jam ke jam.
3. **Melihat Time Series Titik**:
   Klik pada daratan manapun di peta. Sebuah pin akan ditancapkan, dan laci grafik di bagian bawah akan otomatis terbuka menampilkan grafik interaktif ECharts.
4. **Analisis Poligon Penelitian**:
   Klik ikon **Poligon** pada toolbar mengambang di kanan atas peta, buat bentuk poligon mengelilingi daerah aliran sungai (DAS) atau wilayah kajian Anda. Sistem akan memotong grid secara otomatis dan menghitung statistik rata-rata poligon secara instan.
5. **Mengubah Opacity & Layer**:
   Gunakan slider opacity untuk melihat peta dasar jalan/satelit di bawah raster. Centang *Vektor Angin* untuk menampilkan panah angin, dan centang *Batas Wilayah* untuk garis batas provinsi.

---

## ⚡ Arsitektur & Optimasi Kinerja

1. **Penanganan Cloud/Network Storage**: `HDF5_USE_FILE_LOCKING=FALSE` dipasang di inisialisasi awal sehingga dataset dapat dibaca secara langsung tanpa hambatan lock file pada penyimpanan cloud (seperti OneDrive/NFS).
2. **Descending Latitude Resolution**: Slicing xarray secara otomatis mendeteksi apakah urutan latitude tersusun menurun ($6.2 \to -2.7$) atau menaik, memastikan slicing spasial selalu presisi.
3. **In-Memory Image Caching**: Layer raster yang telah dirender disimpan dalam memori LRU cache untuk memastikan perpindahan waktu dan penyesuaian filter berlangsung tanpa latensi.
4. **Keamanan**: Validasi batas koordinat (bounding box), whitelist variabel terdaftar, dan perlindungan dari traversal path file.

---

## 📄 Hak Cipta & Lisensi

&copy; 2025 **Fajri Rinaldi Chan**. All rights reserved.  
Aplikasi Web GIS ini dikembangkan untuk keperluan visualisasi, eksplorasi, dan penelitian analisis hidrometeorologi.
