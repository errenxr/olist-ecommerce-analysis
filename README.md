# Olist E-Commerce Insights — Dashboard Streamlit

Dashboard interaktif untuk menyampaikan hasil analisis pada notebook
`Proyek_Analisis_Data_Annisa_Nabila_Putri.ipynb` (E-Commerce Public Dataset, Olist).
Tampilan mengikuti **CreateSpace Design System** (`createspace-DESIGN.md`).

## Pertanyaan bisnis yang dijawab

1. Bagaimana hubungan antara keterlambatan pengiriman, durasi pengiriman, dan skor ulasan
   pelanggan (Sep 2016 – Agu 2018), serta aspek pengiriman mana yang perlu diprioritaskan?
2. Kategori produk apa yang menghasilkan pendapatan terbesar dan terendah, dan bagaimana
   perubahan pendapatan serta jumlah pesanan per kategori dapat dipakai untuk menentukan
   prioritas promosi dan pengelolaan produk?

## Fitur

| Tab | Isi |
| --- | --- |
| Ringkasan | KPI utama, tren bulanan pendapatan & pesanan, dua temuan utama |
| Pengiriman & Ulasan | Distribusi durasi, skor per ketepatan & tingkat keterlambatan, komposisi 1★–5★, skor per durasi, peta panas durasi × ketepatan, tren bulanan, prioritas aksi |
| Kategori Produk | Top/Bottom N (pendapatan atau pesanan), tren bulanan per kategori, perbandingan Top 5, gelembung pesanan vs pendapatan, tabel lengkap + unduh CSV |
| Kesimpulan | Kesimpulan notebook + bukti pada periode terpilih, tiga action item |
| Data & Metode | Definisi metrik, alur pengolahan, ringkasan kualitas data, pratinjau data |

Filter periode (rentang bulan) ada di sidebar dan berlaku untuk semua tab.

## Struktur folder

```
.
├── dashboard.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml        # tema dasar (warna primer, latar, teks)
└── data/                  # letakkan 5 file CSV di sini
    ├── orders_dataset.csv
    ├── order_reviews_dataset.csv
    ├── order_items_dataset.csv
    ├── products_dataset.csv
    └── product_category_name_translation.csv
```

CSV boleh berada di dalam subfolder `data/` (mis. `data/E-Commerce Public Dataset/`);
dashboard mencarinya secara otomatis. Berkas `.streamlit/config.toml` harus berada di folder
tempat perintah `streamlit run` dijalankan.

## Cara menjalankan

1. **Pastikan Python 3.9+ terpasang**, lalu (disarankan) buat virtual environment:

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

2. **Pasang library**

   ```bash
   pip install -r requirements.txt
   ```

3. **Siapkan data.** Ekstrak dataset (ZIP) lalu salin kelima CSV di atas ke folder `data/`.
   Alternatif: lewati langkah ini, jalankan dashboard, lalu unggah ZIP/CSV melalui panel
   unggah yang muncul. Anda juga dapat menunjuk folder lain dengan variabel lingkungan
   `OLIST_DATA_DIR`:

   ```bash
   # macOS / Linux
   OLIST_DATA_DIR="/path/ke/folder/data" streamlit run dashboard.py
   # Windows PowerShell
   $env:OLIST_DATA_DIR="C:\path\ke\folder\data"; streamlit run dashboard.py
   ```

4. **Jalankan dashboard**

   ```bash
   streamlit run dashboard.py
   ```

   Buka alamat yang tampil di terminal (biasanya http://localhost:8501).

## Catatan metodologi

- Periode analisis: pembelian 1 Sep 2016 – 31 Agu 2018, sama dengan notebook.
- Durasi pengiriman = tanggal diterima − tanggal pembelian; keterlambatan = tanggal diterima −
  tanggal estimasi (terlambat bila > 0 hari).
- Skor ulasan dihitung per pesanan (rata-rata bila ada lebih dari satu ulasan); pesanan tanpa
  ulasan dikecualikan dari analisis skor.
- Pendapatan = jumlah `price` pada pesanan berstatus *delivered* (tanpa ongkos kirim), dalam
  Real Brasil (R$). Nama kategori memakai terjemahan Inggris; bila tidak ada, nama asli;
  produk tanpa kategori diberi label `unknown`.
- Beberapa grafik merupakan **analisis tambahan** di luar notebook: peta panas durasi × ketepatan,
  tren bulanan keterlambatan vs skor, korelasi Spearman, komposisi skor, dan grafik gelembung
  kategori. Seluruh angka inti (mis. 99.421 pesanan, 8,11% terlambat, skor 2,57 vs 4,29,
  pendapatan R$ 13.221.498,11) telah dicocokkan dengan output notebook.

## Catatan teknis

- `matplotlib` dan `seaborn` tetap tercantum di `requirements.txt` karena dipakai pada notebook;
  dashboard sendiri menggambar grafik dengan Plotly.
- Font Poppins, DM Sans, dan Fira Code dimuat dari Google Fonts; tanpa internet, tampilan
  memakai font sistem sebagai cadangan.
- Diuji dengan Python 3.12, Streamlit 1.66, Plotly 7.1, pandas 3.0, dan numpy 2.4.
