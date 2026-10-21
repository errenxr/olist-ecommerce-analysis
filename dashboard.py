"""
Dashboard Analisis Data E-Commerce (Olist) – Streamlit
=====================================================
Sumber analisis : Proyek_Analisis_Data_Annisa_Nabila_Putri.ipynb
Tema visual     : CreateSpace Design System (createspace-DESIGN.md)

Pertanyaan bisnis yang dijawab
1. Bagaimana hubungan antara keterlambatan pengiriman, durasi pengiriman, dan
   skor ulasan pelanggan (Sep 2016 – Agu 2018), serta aspek pengiriman mana
   yang perlu diprioritaskan?
2. Kategori produk apa yang menghasilkan pendapatan terbesar & terendah, dan
   bagaimana perubahan pendapatan serta jumlah pesanan per kategori dapat
   dipakai untuk menentukan prioritas promosi & pengelolaan produk?

Jalankan:  streamlit run dashboard.py
"""
from __future__ import annotations

import inspect
import os
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# =============================================================================
# 1. KONSTANTA
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent

START_DATE = pd.Timestamp("2016-09-01")  # sama dengan notebook
END_DATE = pd.Timestamp("2018-09-01")    # eksklusif → s.d. Agustus 2018

REQUIRED_FILES = {
    "orders": "orders_dataset.csv",
    "reviews": "order_reviews_dataset.csv",
    "order_items": "order_items_dataset.csv",
    "products": "products_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

DATETIME_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

STATUS_ONTIME = "Tepat waktu / lebih awal"
STATUS_LATE = "Terlambat"
DELAY_LABELS = [
    STATUS_ONTIME,
    "Terlambat 1–3 hari",
    "Terlambat 4–7 hari",
    "Terlambat 8–14 hari",
    "Terlambat >14 hari",
]
DURATION_LABELS = ["1–3 hari", "4–7 hari", "8–14 hari", "15–21 hari", ">21 hari"]

# Palet CreateSpace
C_PRIMARY = "#E11D48"
C_SECONDARY = "#2563EB"
C_TERTIARY = "#FACC15"
C_SUCCESS = "#16A34A"
C_WARNING = "#D97706"
C_ERROR = "#DC2626"
C_INK = "#1F2937"
C_MUTED = "#6B7280"
C_LINE = "#E5E7EB"
C_GRAY = "#9CA3AF"
# Seri kategorikal (hanya warna dari sistem desain + varian teks chip)
SERIES = [C_PRIMARY, C_SECONDARY, C_TERTIARY, C_SUCCESS, C_WARNING,
          "#9F1239", "#1E40AF", "#166534"]
RED_RAMP = ["#FDA4AF", "#FB7185", C_PRIMARY, "#9F1239"]  # tint merah (1 warna brand)
MONTHS_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
             "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

PLOT_CONFIG = {"displaylogo": False,
               "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}

# =============================================================================
# 2. UTILITAS FORMAT & KOMPATIBILITAS
# =============================================================================
def month_label(ym: str) -> str:
    year, month = ym.split("-")
    return f"{MONTHS_ID[int(month) - 1]} {year}"


def fmt_int(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def fmt_num(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_money(x: float) -> str:
    if abs(x) >= 1e6:
        return f"R$ {fmt_num(x / 1e6, 2)} jt"
    if abs(x) >= 1e3:
        return f"R$ {fmt_num(x / 1e3, 1)} rb"
    return f"R$ {fmt_num(x, 2)}"


def fmt_pct(x: float, d: int = 2) -> str:
    return f"{fmt_num(x, d)}%"


def _stretch(func) -> dict:
    """Kompatibel lintas versi Streamlit (width='stretch' vs use_container_width)."""
    params = inspect.signature(func).parameters
    return {"width": "stretch"} if "width" in params else {"use_container_width": True}


def show_chart(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, key=key, config=PLOT_CONFIG, **_stretch(st.plotly_chart))


def show_table(df: pd.DataFrame, **kwargs) -> None:
    st.dataframe(df, **_stretch(st.dataframe), **kwargs)


def html(markup: str) -> None:
    """Render HTML tanpa indentasi (agar tidak dibaca sebagai blok kode markdown)."""
    flat = " ".join(line.strip() for line in markup.strip().splitlines())
    st.markdown(flat, unsafe_allow_html=True)


# =============================================================================
# 3. KOMPONEN UI (CreateSpace)
# =============================================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Fira+Code:wght@400;500&family=Poppins:wght@400;500;600;700;800&display=swap');
:root{
  --primary:#E11D48; --secondary:#2563EB; --tertiary:#FACC15;
  --success:#16A34A; --warning:#D97706; --error:#DC2626;
  --ink:#1F2937; --muted:#6B7280; --line:#E5E7EB;
  --glass:rgba(255,255,255,.65);
  --shadow-glass:0 8px 32px rgba(0,0,0,.08);
  --shadow-md:0 4px 16px rgba(0,0,0,.10);
  --shadow-lg:0 12px 40px rgba(0,0,0,.15);
  --shadow-color:0 8px 24px rgba(225,29,72,.25);
  --focus:0 0 0 3px rgba(37,99,235,.35);
}
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
.stApp button, [data-testid="stMarkdownContainer"]{font-family:'DM Sans',system-ui,sans-serif;}
.stApp{
  color:var(--ink);
  background:
    radial-gradient(900px 520px at 6% -6%, rgba(225,29,72,.10), transparent 62%),
    radial-gradient(820px 520px at 100% 8%, rgba(37,99,235,.10), transparent 62%),
    radial-gradient(760px 520px at 62% 102%, rgba(250,204,21,.13), transparent 62%),
    #FFFFFF;
  background-attachment:fixed;
}
.stApp h1,.stApp h2,.stApp h3,.stApp h4{font-family:'Poppins',sans-serif !important;color:var(--ink);}
#MainMenu, footer{visibility:hidden;}
[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:1280px;padding-top:1.4rem;padding-bottom:4rem;}

/* ---------- Hero ---------- */
.hero{position:relative;overflow:hidden;background:var(--primary);border-radius:24px;
  padding:48px;margin-bottom:32px;box-shadow:var(--shadow-color);}
.hero .blob{position:absolute;border-radius:50%;}
.hero .b1{width:360px;height:360px;background:var(--secondary);right:-110px;top:-140px;}
.hero .b2{width:140px;height:140px;background:var(--tertiary);right:36%;bottom:-64px;}
.hero-grid{position:relative;z-index:2;display:grid;grid-template-columns:1.9fr 1fr;gap:32px;align-items:center;}
.hero-title{font-family:'Poppins',sans-serif;font-weight:800;font-size:clamp(36px,4.6vw,72px);
  line-height:1.05;letter-spacing:-.02em;color:#fff;margin:0 0 16px;}
.hero-lead{font-size:18px;line-height:1.6;color:#fff;margin:0;max-width:640px;}
.badge{display:inline-block;background:var(--tertiary);color:var(--ink);font:700 13px 'DM Sans',sans-serif;
  padding:6px 14px;border-radius:9999px;margin-bottom:20px;}
.glass,.hero-glass{background:var(--glass);-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);
  border:1px solid rgba(255,255,255,.3);border-radius:16px;padding:24px;box-shadow:var(--shadow-glass);color:var(--ink);}
.hero-glass-title{font:600 13px 'DM Sans',sans-serif;text-transform:uppercase;letter-spacing:.08em;color:#9F1239;margin-bottom:8px;}
.hero-stat{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:10px 0;border-bottom:1px solid rgba(31,41,55,.14);}
.hero-stat:last-child{border-bottom:none;}
.hero-stat span{font:500 14px 'DM Sans',sans-serif;color:var(--ink);}
.hero-stat b{font:700 20px 'Poppins',sans-serif;color:var(--ink);white-space:nowrap;}

/* ---------- Section ---------- */
.sec{margin:44px 0 20px;}
.sec-num{display:inline-block;background:var(--tertiary);color:var(--ink);font:700 13px 'Poppins',sans-serif;
  padding:4px 12px;border-radius:9999px;}
.sec-title{font:600 32px/1.2 'Poppins',sans-serif;margin:10px 0 6px;color:var(--ink);}
.sec-desc{font:400 16px/1.6 'DM Sans',sans-serif;color:var(--muted);max-width:860px;}

/* ---------- KPI ---------- */
.kpi{position:relative;height:100%;min-height:136px;overflow:hidden;background:var(--glass);-webkit-backdrop-filter:blur(16px);
  backdrop-filter:blur(16px);border:1px solid var(--line);border-radius:16px;padding:22px 22px 20px 28px;
  box-shadow:var(--shadow-glass);transition:transform 200ms ease,box-shadow 200ms ease;}
.kpi:hover{transform:scale(1.02);box-shadow:var(--shadow-md);}
.kpi::before{content:"";position:absolute;left:0;top:0;bottom:0;width:6px;background:var(--accent);}
.kpi-red{--accent:var(--primary);} .kpi-blue{--accent:var(--secondary);} .kpi-yellow{--accent:var(--tertiary);}
.kpi-label{font:500 13px/1.5 'DM Sans',sans-serif;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}
.kpi-value{font:700 30px/1.2 'Poppins',sans-serif;color:var(--ink);margin:6px 0 6px;word-break:break-word;}
.kpi-value-sm{font-size:21px !important;line-height:1.3 !important;}
.kpi-sub{font:400 14px/1.5 'DM Sans',sans-serif;color:var(--muted);}

/* ---------- Kartu (st.container key=card_*) ---------- */
div[class*="st-key-card"]{background:var(--glass);-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);
  border:1px solid var(--line);border-radius:16px;padding:24px;box-shadow:var(--shadow-glass);
  transition:box-shadow 200ms ease;}
div[class*="st-key-card"]:hover{box-shadow:var(--shadow-md);}
.ct{font:600 18px/1.3 'Poppins',sans-serif;color:var(--ink);margin:0 0 2px;}
.cs{font:400 13px/1.5 'DM Sans',sans-serif;color:var(--muted);margin:0 0 8px;}

[data-testid="stHorizontalBlock"]{align-items:stretch;}
[data-testid="stColumn"]:has(.kpi) > div,[data-testid="stColumn"]:has(.kpi) [data-testid="stElementContainer"],
[data-testid="stColumn"]:has(.kpi) [data-testid="stMarkdown"],[data-testid="stColumn"]:has(.kpi) [data-testid="stMarkdownContainer"]{height:100%;}
/* ---------- Callout & chip ---------- */
.callout{border-radius:8px;padding:14px 18px;margin:10px 0;border-left:4px solid var(--c);
  background:var(--bg);color:var(--fg);font:400 15px/1.6 'DM Sans',sans-serif;}
.callout b.t{display:block;font:600 15px 'Poppins',sans-serif;margin-bottom:2px;}
.co-info{--c:#2563EB;--bg:#DBEAFE;--fg:#1E40AF;}
.co-success{--c:#16A34A;--bg:#DCFCE7;--fg:#166534;}
.co-warning{--c:#D97706;--bg:#FEF3C7;--fg:#92400E;}
.co-error{--c:#DC2626;--bg:#FEF2F2;--fg:#991B1B;}
.chip{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 12px;margin:2px 6px 2px 0;
  border-radius:9999px;font:500 13px 'DM Sans',sans-serif;white-space:nowrap;}
.chip-active{background:#DBEAFE;color:#1E40AF;} .chip-complete{background:#DCFCE7;color:#166534;}
.chip-review{background:#FEF3C7;color:#92400E;} .chip-archived{background:#F3F4F6;color:#6B7280;}
.chip-primary{background:#E11D48;color:#fff;}
.q-panel{border-left:6px solid var(--primary);}
.q-panel .q-label{font:600 13px 'DM Sans',sans-serif;text-transform:uppercase;letter-spacing:.08em;color:var(--primary);}
.q-panel .q-text{font:500 17px/1.6 'DM Sans',sans-serif;color:var(--ink);margin-top:4px;}
.step{display:flex;gap:14px;align-items:flex-start;margin:10px 0;}
.step-n{flex:0 0 36px;height:36px;border-radius:9999px;background:var(--primary);color:#fff;
  font:700 15px 'Poppins',sans-serif;display:flex;align-items:center;justify-content:center;}
.step-n.blue{background:var(--secondary);}
.step-b{font:400 15px/1.6 'DM Sans',sans-serif;color:var(--ink);}
.step-b b{font-family:'Poppins',sans-serif;font-weight:600;}
.foot{margin-top:56px;padding:20px 0;border-top:1px solid var(--line);color:var(--muted);font:400 13px 'DM Sans',sans-serif;}

/* ---------- Tab (kompatibel BaseWeb lama & atribut role baru) ---------- */
.stTabs [data-baseweb="tab-list"],.stTabs [role="tablist"]{gap:6px;background:var(--glass);-webkit-backdrop-filter:blur(16px);
  backdrop-filter:blur(16px);padding:6px;border-radius:9999px;border:1px solid var(--line);
  width:fit-content;max-width:100%;overflow-x:auto;box-shadow:var(--shadow-glass);}
.stTabs div:has(> [role="tablist"]){border-bottom:none !important;box-shadow:none !important;}
.stTabs [data-baseweb="tab"],.stTabs [role="tab"]{height:40px;border-radius:9999px !important;padding:0 18px;
  transition:all 150ms ease;background:transparent;border:none !important;}
.stTabs [data-baseweb="tab"] p,.stTabs [role="tab"] p{font:600 14px 'Poppins',sans-serif;color:var(--ink);margin:0;}
.stTabs [data-baseweb="tab"]:hover,.stTabs [role="tab"]:hover{background:rgba(225,29,72,.08);}
.stTabs [aria-selected="true"]{background:var(--primary) !important;box-shadow:var(--shadow-color);}
.stTabs [aria-selected="true"] p{color:#fff !important;}
.stTabs [role="tab"]::after,.stTabs [role="tab"]::before,.stTabs [role="tablist"]::after{display:none !important;}
.stTabs [class*="SelectionIndicator"]{display:none !important;}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none;}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"]{background:rgba(255,255,255,.78);-webkit-backdrop-filter:blur(16px);
  backdrop-filter:blur(16px);border-right:1px solid var(--line);}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:8px;}
.brand-logo{width:44px;height:44px;border-radius:12px;background:var(--primary);color:#fff;
  display:flex;align-items:center;justify-content:center;font:800 22px 'Poppins',sans-serif;box-shadow:var(--shadow-color);}
.brand-name{font:700 18px/1.2 'Poppins',sans-serif;color:var(--ink);}
.brand-sub{font:400 13px 'DM Sans',sans-serif;color:var(--muted);}

/* ---------- Widget ---------- */
.stButton>button,.stDownloadButton>button{border-radius:8px;height:40px;padding:0 20px;font-weight:700;transition:all 150ms ease;}
[data-testid="stBaseButton-primary"]{background:var(--primary);color:#fff;border:none;}
[data-testid="stBaseButton-secondary"]{background:transparent;color:var(--primary);border:1.5px solid var(--primary);}
[data-testid="stBaseButton-secondary"]:hover{background:rgba(225,29,72,.07);color:var(--primary);border-color:var(--primary);}
[data-baseweb="input"],[data-baseweb="select"]>div{border-radius:8px !important;}
[data-baseweb="input"]{border:1.5px solid #D1D5DB !important;background:#fff;}
[data-baseweb="input"]:focus-within{border-color:var(--secondary) !important;box-shadow:var(--focus);}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:8px;overflow:hidden;}
[data-testid="stFileUploader"] section{border-radius:16px;border:1.5px dashed #D1D5DB;background:rgba(255,255,255,.7);}

@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
  .kpi,.glass,.hero-glass,div[class*="st-key-card"],.stTabs [data-baseweb="tab-list"],
  section[data-testid="stSidebar"]{background:rgba(255,255,255,.96);}
}
@media (max-width:900px){
  .hero{padding:28px;} .hero-grid{grid-template-columns:1fr;} .sec-title{font-size:26px;}
}
@media (prefers-reduced-motion:reduce){*{transition:none !important;}}
</style>
"""

_card_counter = {"n": 0}


@contextmanager
def card():
    """Kartu glassmorphism untuk membungkus grafik/tabel."""
    _card_counter["n"] += 1
    with st.container(key=f"card_{_card_counter['n']}"):
        yield


def chart_title(title: str, subtitle: str = "") -> None:
    html(f'<div class="ct">{title}</div><div class="cs">{subtitle}</div>')


def section(num: str, title: str, desc: str = "") -> None:
    html(f'<div class="sec"><span class="sec-num">{num}</span>'
         f'<div class="sec-title">{title}</div><div class="sec-desc">{desc}</div></div>')


def kpi_html(label: str, value: str, sub: str = "", accent: str = "red") -> str:
    small = " kpi-value-sm" if len(value) > 14 and "<" not in value else ""
    value = value.replace("_", "_<wbr>") if "<" not in value else value
    return (f'<div class="kpi kpi-{accent}"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value{small}">{value}</div><div class="kpi-sub">{sub}</div></div>')


def kpi_row(items: list[tuple]) -> None:
    cols = st.columns(len(items), gap="medium")
    for col, item in zip(cols, items):
        col.markdown(kpi_html(*item), unsafe_allow_html=True)


def callout(kind: str, title: str, body: str) -> None:
    html(f'<div class="callout co-{kind}"><b class="t">{title}</b>{body}</div>')


def chip(text: str, kind: str = "active") -> str:
    return f'<span class="chip chip-{kind}">{text}</span>'


def question_panel(label: str, text: str) -> None:
    html(f'<div class="glass q-panel"><div class="q-label">{label}</div><div class="q-text">{text}</div></div>')


# =============================================================================
# 4. PEMUATAN & PERSIAPAN DATA (mengikuti langkah di notebook)
# =============================================================================
def locate_csvs(extra_dir: str | None = None) -> dict:
    """Cari kelima CSV yang dibutuhkan. Urutan: OLIST_DATA_DIR → unggahan → ./data → dst."""
    folders: list[tuple[Path, bool]] = []
    env_dir = os.getenv("OLIST_DATA_DIR")
    if env_dir:
        folders.append((Path(env_dir), True))
    if extra_dir:
        folders.append((Path(extra_dir), True))
    folders += [
        (BASE_DIR / "data", True),
        (BASE_DIR.parent / "data", True),
        (BASE_DIR / "E-Commerce Public Dataset", True),
        (BASE_DIR, False),
    ]
    found = {}
    for key, fname in REQUIRED_FILES.items():
        for folder, recursive in folders:
            if not folder.is_dir():
                continue
            hits = sorted(folder.rglob(fname)) if recursive else sorted(folder.glob(fname))
            if hits:
                found[key] = str(hits[0])
                break
    return found


def save_uploads(files) -> str:
    """Simpan CSV/ZIP unggahan ke folder sementara (hanya nama file yang dikenali)."""
    target = Path(tempfile.mkdtemp(prefix="olist_upload_"))
    wanted = set(REQUIRED_FILES.values())
    for f in files:
        if f.name.lower().endswith(".zip"):
            with zipfile.ZipFile(f) as zf:
                for member in zf.namelist():
                    base = os.path.basename(member)
                    if base in wanted:
                        (target / base).write_bytes(zf.read(member))
        elif f.name in wanted:
            (target / f.name).write_bytes(f.getvalue())
    return str(target)


def prepare_data(orders, reviews, order_items, products, translation) -> dict:
    """Replikasi alur wrangling → cleaning → EDA di notebook."""
    # ---- Kualitas data (sebelum pembersihan) --------------------------------
    untranslated = set(products["product_category_name"].dropna().unique()) - set(
        translation["product_category_name"].dropna().unique())
    quality = pd.DataFrame(
        [
            ("orders", orders, "Kolom tanggal bertipe object; missing value pada 3 kolom tanggal "
                               "(terbanyak pada status selain delivered)",
             "Kolom tanggal dikonversi ke datetime"),
            ("order_reviews", reviews, "Missing pada kolom judul/komentar (tidak dipakai); "
                                       "skor ulasan valid (1–5)",
             "Tidak ada pembersihan"),
            ("order_items", order_items, "Tidak ada missing/duplikat; harga > 0",
             "Tidak ada pembersihan"),
            ("products", products, "Missing pada product_category_name",
             "Diisi label 'unknown'"),
            ("category_translation", translation,
             f"{len(untranslated)} kategori produk tidak punya terjemahan",
             "Memakai nama kategori asli"),
        ],
        columns=["Tabel", "_df", "Temuan", "Tindakan"],
    )
    quality["Jumlah baris"] = quality["_df"].map(len)
    quality["Sel kosong"] = quality["_df"].map(lambda d: int(d.isna().sum().sum()))
    quality["Baris duplikat"] = quality["_df"].map(lambda d: int(d.duplicated().sum()))
    quality = quality[["Tabel", "Jumlah baris", "Sel kosong", "Baris duplikat", "Temuan", "Tindakan"]]

    # ---- Cleaning ------------------------------------------------------------
    orders = orders.copy()
    for col in DATETIME_COLS:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")
    products = products.copy()
    products["product_category_name"] = products["product_category_name"].fillna("unknown")

    # ---- Pertanyaan 1: pengiriman vs ulasan ---------------------------------
    reviews_per_order = reviews.groupby("order_id", as_index=False).agg(
        review_score=("review_score", "mean"))
    purchase = orders["order_purchase_timestamp"]
    orders_period = orders[(purchase >= START_DATE) & (purchase < END_DATE)].copy()
    delivery = orders_period.merge(reviews_per_order, on="order_id", how="left",
                                   validate="one_to_one")
    delivery["delivery_duration_days"] = (
        delivery["order_delivered_customer_date"] - delivery["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    delivery["delivery_delay_days"] = (
        delivery["order_delivered_customer_date"] - delivery["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    delivery["is_valid"] = (
        delivery["order_delivered_customer_date"].notna()
        & delivery["order_estimated_delivery_date"].notna()
        & delivery["order_purchase_timestamp"].notna()
    )
    delivery["delivery_status"] = np.where(
        delivery["is_valid"],
        np.where(delivery["delivery_delay_days"] > 0, STATUS_LATE, STATUS_ONTIME),
        None,
    )
    delivery["delay_group"] = pd.cut(
        delivery["delivery_delay_days"], bins=[-np.inf, 0, 3, 7, 14, np.inf], labels=DELAY_LABELS)
    delivery["duration_group"] = pd.cut(
        delivery["delivery_duration_days"], bins=[0, 3, 7, 14, 21, np.inf],
        labels=DURATION_LABELS, right=True)
    delivery["purchase_month"] = delivery["order_purchase_timestamp"].dt.to_period("M").astype(str)
    delivery = delivery[[
        "order_id", "order_status", "purchase_month", "review_score", "is_valid",
        "delivery_duration_days", "delivery_delay_days", "delivery_status",
        "delay_group", "duration_group",
    ]]

    # ---- Pertanyaan 2: pendapatan per kategori ------------------------------
    orders_sales = orders.loc[
        (orders["order_status"] == "delivered")
        & (purchase >= START_DATE) & (purchase < END_DATE),
        ["order_id", "order_purchase_timestamp"],
    ]
    products_translated = products.merge(translation, on="product_category_name", how="left")
    products_translated["category_label"] = products_translated[
        "product_category_name_english"].fillna(products_translated["product_category_name"])
    sales = (
        order_items[["order_id", "product_id", "price"]]
        .merge(orders_sales, on="order_id", how="inner", validate="many_to_one")
        .merge(products_translated[["product_id", "category_label"]],
               on="product_id", how="left", validate="many_to_one")
    )
    sales["category_label"] = sales["category_label"].fillna("unknown")
    sales["purchase_month"] = sales["order_purchase_timestamp"].dt.to_period("M").astype(str)
    sales = sales.drop(columns="order_purchase_timestamp")

    return {"delivery": delivery, "sales": sales, "quality": quality}


@st.cache_data(show_spinner="Memuat dan membersihkan data…")
def load_data(paths: tuple) -> dict:
    p = dict(paths)
    raw = {k: pd.read_csv(p[k]) for k in REQUIRED_FILES}
    return prepare_data(raw["orders"], raw["reviews"], raw["order_items"],
                        raw["products"], raw["translation"])


def category_table(sales: pd.DataFrame) -> pd.DataFrame:
    cat = sales.groupby("category_label").agg(
        revenue=("price", "sum"),
        order_count=("order_id", "nunique"),
        item_count=("product_id", "size"),
    )
    cat["revenue_share_pct"] = cat["revenue"] / cat["revenue"].sum() * 100
    cat["rank_revenue"] = cat["revenue"].rank(method="min", ascending=False).astype(int)
    cat["rank_orders"] = cat["order_count"].rank(method="min", ascending=False).astype(int)
    cat["avg_price_per_item"] = cat["revenue"] / cat["item_count"]
    cat["revenue_per_order"] = cat["revenue"] / cat["order_count"]
    return cat.sort_values("revenue", ascending=False)


# =============================================================================
# 5. GRAFIK (Plotly)
# =============================================================================
def style_fig(fig: go.Figure, height: int = 380, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        template="plotly_white",
        separators=",.",
        font=dict(family="DM Sans, sans-serif", size=13, color=C_INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=12, b=8),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=C_INK, bordercolor=C_INK,
                        font=dict(family="DM Sans, sans-serif", size=13, color="#FFFFFF")),
    )
    fig.update_xaxes(gridcolor=C_LINE, zeroline=False, linecolor="#D1D5DB", automargin=True)
    fig.update_yaxes(gridcolor=C_LINE, zeroline=False, linecolor="#D1D5DB", automargin=True)
    return fig


def month_axis(fig: go.Figure, labels: list) -> None:
    """Tampilkan semua bulan pada sumbu-x (tidak dilompati otomatis)."""
    fig.update_xaxes(type="category", tickmode="array", tickvals=labels, ticktext=labels,
                     tickangle=-45, tickfont=dict(size=11))


def fig_duration_hist(durations: pd.Series, bins: int, cap: float) -> go.Figure:
    shown = durations[durations <= cap]
    counts, edges = np.histogram(shown, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    labels = [f"{fmt_num(a, 1)}–{fmt_num(b, 1)} hari" for a, b in zip(edges[:-1], edges[1:])]
    fig = go.Figure(go.Bar(
        x=centers, y=counts, width=(edges[1] - edges[0]) * 0.94, marker_color=C_SECONDARY,
        customdata=labels, hovertemplate="%{customdata}<br><b>%{y:,.0f}</b> pesanan<extra></extra>"))
    med, mean = durations.median(), durations.mean()
    fig.add_vline(x=med, line_dash="dash", line_color=C_PRIMARY, line_width=2,
                  annotation_text=f"Median {fmt_num(med, 1)} hr", annotation_position="top right",
                  annotation_font_color=C_PRIMARY)
    if mean <= cap:
        fig.add_vline(x=mean, line_dash="dot", line_color=C_INK, line_width=2,
                      annotation_text=f"Rata-rata {fmt_num(mean, 1)} hr",
                      annotation_position="top right", annotation_font_color=C_INK,
                      annotation_yshift=-22)
    fig.update_xaxes(title="Durasi dari pembelian hingga diterima (hari)")
    fig.update_yaxes(title="Jumlah pesanan")
    return style_fig(fig, 380)


def fig_box_status(rv: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for status, color in [(STATUS_ONTIME, C_SECONDARY), (STATUS_LATE, C_PRIMARY)]:
        s = rv.loc[rv["delivery_status"] == status, "review_score"]
        if s.empty:
            continue
        q1, med, q3 = s.quantile([.25, .5, .75])
        iqr = q3 - q1
        lo = s[s >= q1 - 1.5 * iqr].min()
        hi = s[s <= q3 + 1.5 * iqr].max()
        fig.add_trace(go.Box(
            name=status, x=[status], q1=[q1], median=[med], q3=[q3],
            lowerfence=[lo], upperfence=[hi], mean=[s.mean()], boxmean=True,
            marker_color=color, line=dict(color=color), fillcolor=color,
            opacity=.85, hovertemplate=f"{status}<br>Rata-rata: {fmt_num(s.mean())}<extra></extra>"))
    fig.update_yaxes(title="Skor ulasan", range=[0.8, 5.2], dtick=1)
    fig.update_xaxes(title="")
    return style_fig(fig, 380)


def fig_delay_bar(df: pd.DataFrame, overall: float) -> go.Figure:
    colors = [C_SECONDARY] + RED_RAMP
    fig = go.Figure(go.Bar(
        x=df.index.astype(str), y=df["rata_rata"], marker_color=colors[:len(df)],
        text=[fmt_num(v) for v in df["rata_rata"]], textposition="outside",
        customdata=np.stack([df["jumlah"], df["median"]], axis=-1),
        hovertemplate="%{x}<br>Rata-rata skor: <b>%{y:.2f}</b><br>Median: %{customdata[1]:.0f}"
                      "<br>Pesanan: %{customdata[0]:,.0f}<extra></extra>"))
    fig.add_hline(y=overall, line_dash="dash", line_color=C_MUTED,
                  annotation_text=f"Rata-rata keseluruhan {fmt_num(overall)}",
                  annotation_position="top right", annotation_font_color=C_MUTED)
    fig.update_yaxes(title="Rata-rata skor ulasan", range=[0, 5.6], dtick=1)
    fig.update_xaxes(title="Kelompok keterlambatan", tickangle=-20)
    return style_fig(fig, 380)


def fig_score_mix(rv: pd.DataFrame) -> go.Figure:
    tmp = rv.assign(score=np.floor(rv["review_score"] + 0.5).astype(int))
    mix = (tmp.groupby(["delay_group", "score"], observed=False).size()
           .unstack(fill_value=0).reindex(columns=[1, 2, 3, 4, 5], fill_value=0))
    share = mix.div(mix.sum(axis=1).replace(0, np.nan), axis=0) * 100
    palette = {1: C_PRIMARY, 2: "#FDA4AF", 3: "#E5E7EB", 4: "#93C5FD", 5: C_SECONDARY}
    fig = go.Figure()
    for score in [1, 2, 3, 4, 5]:
        fig.add_trace(go.Bar(
            name=f"{score} ★", x=share.index.astype(str), y=share[score].fillna(0),
            marker_color=palette[score],
            hovertemplate="%{x}<br>Skor " + str(score) + ": <b>%{y:.1f}%</b><extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="Porsi ulasan (%)", range=[0, 100])
    fig.update_xaxes(title="Kelompok keterlambatan", tickangle=-20)
    return style_fig(fig, 380, legend=True)


def fig_duration_bar(df: pd.DataFrame) -> go.Figure:
    low = df["rata_rata"].idxmin()
    colors = [C_PRIMARY if i == low else C_SECONDARY for i in df.index]
    fig = go.Figure(go.Bar(
        x=df.index.astype(str), y=df["rata_rata"], marker_color=colors,
        text=[fmt_num(v) for v in df["rata_rata"]], textposition="outside",
        customdata=df["jumlah"],
        hovertemplate="%{x}<br>Rata-rata skor: <b>%{y:.2f}</b><br>Pesanan: %{customdata:,.0f}<extra></extra>"))
    fig.update_yaxes(title="Rata-rata skor ulasan", range=[0, 5.6], dtick=1)
    fig.update_xaxes(title="Kelompok durasi pengiriman")
    return style_fig(fig, 380)


def fig_heatmap(rv: pd.DataFrame, min_n: int = 30) -> tuple[go.Figure, pd.DataFrame, pd.DataFrame]:
    g = rv.groupby(["duration_group", "delivery_status"], observed=False).agg(
        avg=("review_score", "mean"), n=("order_id", "size")).reset_index()
    avg = g.pivot(index="duration_group", columns="delivery_status", values="avg")
    n = g.pivot(index="duration_group", columns="delivery_status", values="n").fillna(0)
    cols = [c for c in [STATUS_ONTIME, STATUS_LATE] if c in avg.columns]
    avg, n = avg[cols], n[cols]
    z = avg.where(n >= min_n)
    text = [[(f"<b>{fmt_num(avg.iloc[i, j])}</b><br>n={fmt_int(n.iloc[i, j])}"
              if n.iloc[i, j] >= min_n else f"n&lt;{min_n}") for j in range(len(cols))]
            for i in range(len(avg))]
    fig = go.Figure(go.Heatmap(
        z=z.values, x=cols, y=[str(i) for i in avg.index], text=text, texttemplate="%{text}",
        textfont=dict(size=13, color=C_INK),
        colorscale=[[0, C_PRIMARY], [.5, "#F3F4F6"], [1, C_SECONDARY]], zmin=1, zmax=5,
        xgap=4, ygap=4, colorbar=dict(title="Skor", thickness=12),
        hovertemplate="Durasi %{y}<br>%{x}<br>Rata-rata skor: %{z:.2f}<extra></extra>"))
    fig.update_yaxes(title="Durasi pengiriman", autorange="reversed")
    fig.update_xaxes(title="")
    return style_fig(fig, 380), avg, n


def fig_monthly_q1(valid: pd.DataFrame, rv: pd.DataFrame, min_orders: int = 30) -> go.Figure | None:
    m = (valid.assign(is_late=valid["delivery_delay_days"] > 0)
         .groupby("purchase_month").agg(orders=("order_id", "size"), late_pct=("is_late", "mean")))
    m["late_pct"] *= 100
    m["avg_review"] = rv.groupby("purchase_month")["review_score"].mean()
    m = m[m["orders"] >= min_orders]
    if m.empty:
        return None
    x = [month_label(i) for i in m.index]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=x, y=m["late_pct"], name="% pesanan terlambat", marker_color="#FDA4AF",
                         hovertemplate="%{x}<br>Terlambat: <b>%{y:.2f}%</b><extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=x, y=m["avg_review"], name="Rata-rata skor ulasan", mode="lines+markers",
                             line=dict(color=C_SECONDARY, width=3), marker=dict(size=7),
                             hovertemplate="%{x}<br>Skor: <b>%{y:.2f}</b><extra></extra>"), secondary_y=True)
    fig.update_yaxes(title="% pesanan terlambat", secondary_y=False, ticksuffix="%")
    fig.update_yaxes(title="Rata-rata skor ulasan", secondary_y=True, range=[1, 5], dtick=1, showgrid=False)
    month_axis(fig, x)
    return style_fig(fig, 380, legend=True)


def fig_barh(series: pd.Series, color: str, xtitle: str, money: bool) -> go.Figure:
    s = series.sort_values()
    texts = [fmt_money(v) if money else fmt_int(v) for v in s]
    fig = go.Figure(go.Bar(
        x=s.values, y=s.index, orientation="h", marker_color=color, text=texts, textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br><b>" + ("R$ %{x:,.2f}" if money else "%{x:,.0f}") + "</b><extra></extra>"))
    fig.update_xaxes(title=xtitle, range=[0, float(s.max()) * 1.45 if s.max() > 0 else 1])
    fig.update_yaxes(title="")
    return style_fig(fig, max(320, 34 * len(s) + 90))


def fig_monthly_category(monthly: pd.DataFrame, cats: list, months: list, metric: str) -> go.Figure:
    pivot = (monthly.pivot(index="purchase_month", columns="category_label", values=metric)
             .reindex(months).fillna(0))
    x = [month_label(m) for m in pivot.index]
    fig = go.Figure()
    for i, cat in enumerate(cats):
        if cat not in pivot.columns:
            continue
        fig.add_trace(go.Scatter(
            x=x, y=pivot[cat], name=cat, mode="lines+markers",
            line=dict(color=SERIES[i % len(SERIES)], width=3), marker=dict(size=6),
            hovertemplate="%{x}<br>" + cat + ": <b>%{y:,.0f}</b><extra></extra>"))
    fig.update_xaxes(tickangle=-40)
    fig.update_yaxes(title="Pendapatan produk (R$)" if metric == "revenue" else "Pesanan unik")
    month_axis(fig, x)
    return style_fig(fig, 400, legend=True)


def fig_scatter(cat: pd.DataFrame, log: bool) -> go.Figure:
    top_orders = set(cat.sort_values("order_count", ascending=False).head(5).index)
    top_rev = set(cat.sort_values("revenue", ascending=False).head(5).index)
    both, either = top_orders & top_rev, (top_orders | top_rev) - (top_orders & top_rev)
    groups = [("Top 5 di kedua metrik", both, C_PRIMARY, True),
              ("Top 5 di salah satu metrik", either, C_SECONDARY, True),
              ("Kategori lain", set(cat.index) - both - either, C_GRAY, False)]
    max_items = max(float(cat["item_count"].max()), 1.0)
    positions = ["top center", "bottom center", "middle right", "middle left", "top right"]
    fig = go.Figure()
    for name, members, color, labelled in groups:
        if not members:
            continue
        d = cat.loc[sorted(members)]
        size = 8 + 30 * np.sqrt(d["item_count"] / max_items)
        fig.add_trace(go.Scatter(
            x=d["order_count"], y=d["revenue"], name=name,
            mode="markers+text" if labelled else "markers",
            text=list(d.index) if labelled else None,
            textposition=[positions[i % len(positions)] for i in range(len(d))] if labelled else None,
            textfont=dict(size=11, color=C_INK),
            marker=dict(size=size, color=color, opacity=.85 if labelled else .55,
                        line=dict(color="#FFFFFF", width=1.2)),
            hovertext=list(d.index),
            customdata=np.stack([d["avg_price_per_item"], d["rank_orders"], d["rank_revenue"]], axis=-1),
            hovertemplate=("<b>%{hovertext}</b><br>Pesanan unik: %{x:,.0f}<br>Pendapatan: R$ %{y:,.0f}"
                           "<br>Rata-rata harga/item: R$ %{customdata[0]:,.2f}"
                           "<br>Peringkat pesanan #%{customdata[1]} · pendapatan #%{customdata[2]}<extra></extra>")))
    fig.update_xaxes(title="Jumlah pesanan unik", type="log" if log else "linear")
    fig.update_yaxes(title="Pendapatan produk (R$)", type="log" if log else "linear")
    if log:  # hanya tampilkan pangkat sepuluh agar sumbu tidak penuh
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(dtick=1)
    return style_fig(fig, 520, legend=True)


def fig_overview(sales: pd.DataFrame, months: list) -> go.Figure:
    m = sales.groupby("purchase_month").agg(revenue=("price", "sum"), orders=("order_id", "nunique")).reindex(months).fillna(0)
    x = [month_label(i) for i in m.index]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=x, y=m["revenue"], name="Pendapatan produk (R$)", marker_color="#93C5FD",
                         hovertemplate="%{x}<br>Pendapatan: <b>R$ %{y:,.0f}</b><extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=x, y=m["orders"], name="Pesanan unik (delivered)", mode="lines+markers",
                             line=dict(color=C_PRIMARY, width=3), marker=dict(size=6),
                             hovertemplate="%{x}<br>Pesanan: <b>%{y:,.0f}</b><extra></extra>"), secondary_y=True)
    fig.update_yaxes(title="Pendapatan (R$)", secondary_y=False)
    fig.update_yaxes(title="Pesanan unik", secondary_y=True, showgrid=False)
    month_axis(fig, x)
    return style_fig(fig, 380, legend=True)


# =============================================================================
# 6. HALAMAN
# =============================================================================
def render_hero(n_orders: int, revenue: float, avg_review: float, period: str) -> None:
    html(f"""
    <div class="hero"><div class="blob b1"></div><div class="blob b2"></div>
      <div class="hero-grid">
        <div>
          <span class="badge">Proyek Analisis Data · E-Commerce Olist</span>
          <div class="hero-title">Olist E&#8209;Commerce Insights</div>
          <p class="hero-lead">Dashboard interaktif untuk melihat bagaimana keterlambatan pengiriman memengaruhi
          ulasan pelanggan, dan kategori produk mana yang menggerakkan pendapatan.</p>
        </div>
        <div class="hero-glass">
          <div class="hero-glass-title">Periode terpilih · {period}</div>
          <div class="hero-stat"><span>Total pesanan</span><b>{fmt_int(n_orders)}</b></div>
          <div class="hero-stat"><span>Pendapatan produk</span><b>{fmt_money(revenue)}</b></div>
          <div class="hero-stat"><span>Rata-rata skor ulasan</span><b>{fmt_num(avg_review)} ★</b></div>
        </div>
      </div>
    </div>""")


def tab_overview(dv, valid, rv, sales, cat, months):
    section("00", "Ringkasan Eksekutif", "Angka kunci untuk periode yang dipilih di sidebar.")
    late_pct = (valid["delivery_delay_days"] > 0).mean() * 100 if len(valid) else float("nan")
    kpi_row([
        ("Total pesanan", fmt_int(len(dv)), f"{fmt_int(dv['review_score'].notna().sum())} pesanan punya ulasan", "red"),
        ("Pendapatan produk", fmt_money(sales["price"].sum()), f"{fmt_int(sales['order_id'].nunique())} pesanan delivered", "blue"),
        ("Pesanan terlambat", fmt_pct(late_pct), f"dari {fmt_int(len(valid))} pesanan terkirim", "yellow"),
        ("Rata-rata skor ulasan", fmt_num(rv["review_score"].mean()) if len(rv) else "–", "skala 1–5", "red"),
    ])
    st.write("")
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        with card():
            chart_title("Tren bulanan: pendapatan & pesanan",
                        "Hanya pesanan berstatus delivered; pendapatan = jumlah harga produk (tanpa ongkir).")
            show_chart(fig_overview(sales, months), "ov_trend")
    with right:
        with card():
            chart_title("Dua temuan utama")
            if len(rv) and (rv["delivery_status"] == STATUS_LATE).any():
                a = rv.loc[rv["delivery_status"] == STATUS_ONTIME, "review_score"].mean()
                b = rv.loc[rv["delivery_status"] == STATUS_LATE, "review_score"].mean()
                callout("error", "Pengiriman · keterlambatan menekan kepuasan",
                        f"Pesanan terlambat rata-rata diberi skor <b>{fmt_num(b)}</b>, sedangkan yang tepat waktu "
                        f"<b>{fmt_num(a)}</b> (selisih {fmt_num(a - b)} poin).")
            if len(cat):
                top = cat.index[0]
                callout("info", "Kategori · pendapatan tertinggi",
                        f"<b>{top}</b> memimpin dengan {fmt_money(cat.iloc[0]['revenue'])} "
                        f"({fmt_pct(cat.iloc[0]['revenue_share_pct'])} dari total). "
                        f"Kategori terendah: <b>{cat.index[-1]}</b> ({fmt_money(cat.iloc[-1]['revenue'])}).")
                top5_o = set(cat.sort_values("order_count", ascending=False).head(5).index)
                top5_r = set(cat.head(5).index)
                callout("warning", "Pesanan terbanyak ≠ pendapatan terbesar",
                        f"{len(top5_o & top5_r)} dari 5 kategori teratas muncul di kedua daftar "
                        f"(pesanan & pendapatan). Lihat tab <b>Kategori Produk</b> untuk detailnya.")
            html('<div class="cs" style="margin-top:8px">Gunakan tab di atas untuk menelusuri tiap pertanyaan bisnis.</div>')


def tab_delivery(dv, valid, rv):
    section("01", "Pengiriman & Kepuasan Pelanggan",
            "Bagaimana keterlambatan dan durasi pengiriman berhubungan dengan skor ulasan?")
    question_panel("Pertanyaan bisnis 1",
                   "Bagaimana hubungan antara keterlambatan pengiriman, durasi pengiriman, dan skor ulasan "
                   "pelanggan pada pesanan e-commerce Olist, serta aspek pengiriman mana yang perlu "
                   "diprioritaskan untuk meningkatkan kepuasan pelanggan?")
    st.write("")
    if rv.empty:
        callout("warning", "Data tidak cukup", "Tidak ada pesanan terkirim dengan ulasan pada periode ini.")
        return

    late = rv[rv["delivery_status"] == STATUS_LATE]
    ontime = rv[rv["delivery_status"] == STATUS_ONTIME]
    avg_late = late["review_score"].mean() if len(late) else float("nan")
    avg_on = ontime["review_score"].mean() if len(ontime) else float("nan")
    late_pct = (valid["delivery_delay_days"] > 0).mean() * 100
    kpi_row([
        ("Pesanan terlambat", fmt_pct(late_pct), f"{fmt_int((valid['delivery_delay_days'] > 0).sum())} dari {fmt_int(len(valid))} pesanan", "red"),
        ("Skor · terlambat", fmt_num(avg_late), f"{fmt_int(len(late))} pesanan", "red"),
        ("Skor · tepat waktu", fmt_num(avg_on), f"{fmt_int(len(ontime))} pesanan", "blue"),
        ("Median durasi kirim", f"{fmt_num(valid['delivery_duration_days'].median(), 1)} hari",
         f"rata-rata {fmt_num(valid['delivery_duration_days'].mean(), 1)} hari", "yellow"),
    ])
    st.write("")

    # ---- Baris 1: distribusi durasi + box ulasan --------------------------------
    c1, c2 = st.columns([1.5, 1], gap="large")
    with c1:
        with card():
            chart_title("Distribusi durasi pengiriman", "Dari pembelian sampai pesanan diterima pelanggan.")
            max_d = float(valid["delivery_duration_days"].max())
            s1, s2 = st.columns(2)
            bins = s1.slider("Jumlah bin", 10, 80, 40, key="q1_bins")
            cap = s2.slider("Tampilkan durasi s.d. (hari)", 20, int(max(30, np.ceil(max_d))),
                            int(min(60, max(30, np.ceil(max_d)))), key="q1_cap")
            n_out = int((valid["delivery_duration_days"] > cap).sum())
            show_chart(fig_duration_hist(valid["delivery_duration_days"], bins, cap), "q1_hist")
            if n_out:
                html(f'<div class="cs">{fmt_int(n_out)} pesanan dengan durasi &gt; {cap} hari tidak digambar '
                     f'(median & rata-rata tetap dihitung dari seluruh data).</div>')
    with c2:
        with card():
            chart_title("Skor ulasan berdasarkan ketepatan", "Kotak = Q1–Q3, garis = median, berlian = rata-rata.")
            show_chart(fig_box_status(rv), "q1_box")

    st.write("")
    # ---- Baris 2: per kelompok keterlambatan ----------------------------------
    grp = (rv.groupby("delay_group", observed=False)
           .agg(jumlah=("order_id", "nunique"), rata_rata=("review_score", "mean"), median=("review_score", "median"))
           .dropna(subset=["rata_rata"]))
    c3, c4 = st.columns(2, gap="large")
    with c3:
        with card():
            chart_title("Rata-rata skor menurut tingkat keterlambatan",
                        "Semakin lama terlambat, skor semakin turun.")
            show_chart(fig_delay_bar(grp, rv["review_score"].mean()), "q1_delay")
    with c4:
        with card():
            chart_title("Komposisi skor menurut tingkat keterlambatan",
                        "Porsi ulasan 1★–5★ pada tiap kelompok (100%).")
            show_chart(fig_score_mix(rv), "q1_mix")

    if len(grp) >= 2:
        first, last = grp.iloc[0], grp.iloc[-1]
        callout("info", "Pola yang terlihat",
                f"Skor rata-rata turun dari <b>{fmt_num(first['rata_rata'])}</b> ({grp.index[0]}) menjadi "
                f"<b>{fmt_num(last['rata_rata'])}</b> ({grp.index[-1]}). Median di kelompok terlambat terlama: "
                f"<b>{fmt_num(last['median'], 0)}</b>.")

    st.write("")
    # ---- Baris 3: durasi + heatmap -------------------------------------------
    dur = (rv.groupby("duration_group", observed=False)
           .agg(jumlah=("order_id", "nunique"), rata_rata=("review_score", "mean"))
           .dropna(subset=["rata_rata"]))
    c5, c6 = st.columns(2, gap="large")
    with c5:
        with card():
            chart_title("Rata-rata skor menurut durasi pengiriman",
                        "Batang merah = kelompok dengan skor terendah.")
            if len(dur):
                show_chart(fig_duration_bar(dur), "q1_dur")
    with c6:
        with card():
            chart_title("Durasi × ketepatan: mana yang lebih berpengaruh?",
                        "Rata-rata skor pada tiap kombinasi (sel dengan n < 30 dikosongkan).")
            hm, avg_hm, n_hm = fig_heatmap(rv)
            show_chart(hm, "q1_heat")

    st.write("")
    # ---- Tren bulanan ------------------------------------------------------------
    with card():
        chart_title("Tren bulanan: keterlambatan vs skor ulasan",
                    "Bulan dengan < 30 pesanan terkirim tidak ditampilkan agar tidak menyesatkan.")
        fm = fig_monthly_q1(valid, rv)
        if fm is None:
            st.info("Belum cukup data bulanan pada periode ini.")
        else:
            show_chart(fm, "q1_month")

    # ---- Prioritas ----------------------------------------------------------------
    section("→", "Aspek pengiriman yang perlu diprioritaskan",
            "Dihitung dari data pada periode terpilih (analisis tambahan di luar notebook).")
    low_share_late = (late["review_score"] <= 2).mean() * 100 if len(late) else float("nan")
    low_share_on = (ontime["review_score"] <= 2).mean() * 100 if len(ontime) else float("nan")
    if len(rv) < 30 or len(late) == 0 or len(ontime) == 0:
        callout("warning", "Sampel terlalu kecil",
                "Pada periode ini jumlah pesanan berulasan terlalu sedikit (atau tidak ada perbandingan "
                "terlambat vs tepat waktu) untuk menyimpulkan prioritas. Perluas rentang bulan di sidebar.")
        return
    rho_delay = rv["delivery_delay_days"].rank().corr(rv["review_score"].rank())
    rho_dur = rv["delivery_duration_days"].rank().corr(rv["review_score"].rank())
    p1, p2 = st.columns(2, gap="large")
    with p1:
        with card():
            html(f"""
            <div class="step"><div class="step-n">1</div><div class="step-b"><b>Kendalikan keterlambatan terhadap estimasi</b><br>
            {fmt_pct(low_share_late, 1)} pesanan terlambat mendapat skor ≤ 2, dibanding {fmt_pct(low_share_on, 1)} pada pesanan tepat waktu.
            Selisih rata-rata skor: <b>{fmt_num(avg_on - avg_late)}</b> poin.</div></div>
            <div class="step"><div class="step-n blue">2</div><div class="step-b"><b>Tekan durasi pengiriman yang sangat panjang</b><br>
            {_long_duration_text(dur, avg_hm, n_hm)}</div></div>""")
    with p2:
        with card():
            stronger = "keterlambatan" if abs(rho_delay) >= abs(rho_dur) else "durasi pengiriman"
            html(f"""
            <div class="ct">Kekuatan hubungan (korelasi peringkat Spearman)</div>
            <div class="cs">Semakin negatif, semakin kuat hubungan “makin lambat → makin rendah skor”.</div>
            <div class="hero-stat" style="border-color:#E5E7EB"><span>Keterlambatan vs skor ulasan</span><b>ρ = {fmt_num(rho_delay, 3)}</b></div>
            <div class="hero-stat" style="border-color:#E5E7EB"><span>Durasi pengiriman vs skor ulasan</span><b>ρ = {fmt_num(rho_dur, 3)}</b></div>""")
            callout("info", "Bacaan",
                    f"Secara korelasi peringkat, hubungan dengan <b>{stronger}</b> tampak lebih kuat. Namun "
                    f"efek keterlambatan bersifat <i>ambang</i>: pesanan yang datang lebih awal dari estimasi "
                    f"hampir tidak memengaruhi skor, sehingga korelasi linear/peringkat cenderung meremehkannya. "
                    f"Peta panas di atas (durasi × ketepatan) memberi gambaran yang lebih adil. "
                    f"Korelasi menunjukkan keterkaitan, bukan sebab-akibat.")
    return


def _long_duration_text(dur: pd.DataFrame, avg_hm: pd.DataFrame, n_hm: pd.DataFrame) -> str:
    if dur.empty or ">21 hari" not in dur.index:
        return "Data kelompok durasi >21 hari tidak tersedia pada periode ini."
    base = f"Pesanan dengan durasi >21 hari rata-rata dinilai <b>{fmt_num(dur.loc['>21 hari', 'rata_rata'])}</b>"
    try:
        a = avg_hm.loc[">21 hari", STATUS_ONTIME]
        b = avg_hm.loc[">21 hari", STATUS_LATE]
        if n_hm.loc[">21 hari", STATUS_ONTIME] >= 30 and n_hm.loc[">21 hari", STATUS_LATE] >= 30:
            return (base + f"; skor <b>{fmt_num(a)}</b> bila tetap sesuai estimasi vs <b>{fmt_num(b)}</b> "
                           f"bila terlambat.")
    except KeyError:
        pass
    return base + "."


def tab_category(sales, cat, months):
    section("02", "Kategori Produk & Pendapatan",
            "Kategori mana yang paling dan paling sedikit menghasilkan pendapatan, dan bagaimana tren-nya?")
    question_panel("Pertanyaan bisnis 2",
                   "Kategori produk apa yang menghasilkan pendapatan terbesar dan terendah, serta bagaimana "
                   "perubahan pendapatan dan jumlah pesanan per kategori dapat digunakan untuk menentukan "
                   "prioritas promosi dan pengelolaan produk?")
    st.write("")
    if cat.empty:
        callout("warning", "Data tidak cukup", "Tidak ada transaksi delivered pada periode ini.")
        return

    cum = cat["revenue_share_pct"].cumsum()
    n80 = int((cum < 80).sum() + 1)
    top5_share = cat.head(5)["revenue_share_pct"].sum()
    kpi_row([
        ("Kategori teratas", cat.index[0], f"{fmt_money(cat.iloc[0]['revenue'])} · {fmt_pct(cat.iloc[0]['revenue_share_pct'])}", "red"),
        ("Kategori terendah", cat.index[-1], f"{fmt_money(cat.iloc[-1]['revenue'])} · {fmt_int(cat.iloc[-1]['order_count'])} pesanan", "blue"),
        ("Kontribusi Top 5", fmt_pct(top5_share, 1), "dari total pendapatan", "yellow"),
        ("Konsentrasi 80%", f"{n80} kategori", f"dari {len(cat)} kategori aktif", "red"),
    ])
    st.write("")

    # ---- Kontrol -----------------------------------------------------------------
    with card():
        k1, k2 = st.columns([1, 1.2], gap="large")
        top_n = k1.slider("Jumlah kategori ditampilkan (Top / Bottom N)", 3, min(20, len(cat)),
                          min(10, len(cat)), key="q2_topn")
        metric_label = k2.radio("Urutkan berdasarkan", ["Pendapatan produk", "Jumlah pesanan unik"],
                                horizontal=True, key="q2_metric")
    metric = "revenue" if metric_label == "Pendapatan produk" else "order_count"
    money = metric == "revenue"
    st.write("")

    # ---- Top / Bottom N ----------------------------------------------------------
    ranked = cat.sort_values(metric, ascending=False)
    top_s = ranked[metric].head(top_n)
    bot_s = ranked[metric].tail(top_n)
    t1, t2 = st.columns(2, gap="large")
    with t1:
        with card():
            chart_title(f"{top_n} kategori tertinggi", f"Berdasarkan {metric_label.lower()}.")
            show_chart(fig_barh(top_s, C_PRIMARY, metric_label, money), "q2_top")
    with t2:
        with card():
            chart_title(f"{top_n} kategori terendah", f"Berdasarkan {metric_label.lower()}.")
            show_chart(fig_barh(bot_s, C_SECONDARY, metric_label, money), "q2_bottom")
    st.write("")

    # ---- Tren ---------------------------------------------------------------------
    monthly = sales.groupby(["purchase_month", "category_label"], as_index=False).agg(
        revenue=("price", "sum"), order_count=("order_id", "nunique"))
    with card():
        chart_title("Tren bulanan per kategori", "Pilih kategori untuk dibandingkan (maks. 8).")
        sel = st.multiselect("Kategori", list(cat.index), default=list(cat.index[:5]),
                             max_selections=8, key="q2_cats")
        if not sel:
            st.info("Pilih minimal satu kategori untuk menampilkan tren.")
        else:
            a, b = st.columns(2, gap="large")
            with a:
                html('<div class="ct" style="font-size:16px">Pendapatan bulanan</div>')
                show_chart(fig_monthly_category(monthly, sel, months, "revenue"), "q2_trend_rev")
            with b:
                html('<div class="ct" style="font-size:16px">Jumlah pesanan bulanan</div>')
                show_chart(fig_monthly_category(monthly, sel, months, "order_count"), "q2_trend_ord")
    st.write("")

    # ---- Perbandingan pesanan vs pendapatan --------------------------------------
    top5_orders = cat.sort_values("order_count", ascending=False).head(5)
    top5_rev = cat.sort_values("revenue", ascending=False).head(5)
    common = [c for c in top5_rev.index if c in top5_orders.index]
    s1, s2 = st.columns([1.15, 1], gap="large")
    with s1:
        with card():
            chart_title("Top 5 berdasarkan pesanan vs pendapatan",
                        "Ukuran gelembung = jumlah item terjual. Aktifkan skala log agar kategori kecil terlihat.")
            log = st.checkbox("Skala logaritmik", value=True, key="q2_log")
            show_chart(fig_scatter(cat, log), "q2_scatter")
    with s2:
        with card():
            chart_title("Daftar peringkat", "Top 5 berdasarkan masing-masing metrik.")
            html("<b>Top 5 pesanan</b><br>" + "".join(chip(f"#{i + 1} {c}", "active") for i, c in enumerate(top5_orders.index)))
            html("<b>Top 5 pendapatan</b><br>" + "".join(chip(f"#{i + 1} {c}", "complete") for i, c in enumerate(top5_rev.index)))
            html("<b>Masuk kedua daftar</b><br>" + ("".join(chip(c, "review") for c in common) if common else chip("Tidak ada", "archived")))
            gap_df = cat[cat["rank_revenue"] <= 10].assign(gap=lambda d: d["rank_orders"] - d["rank_revenue"])
            best = gap_df.sort_values("gap", ascending=False).iloc[0]
            if best["gap"] > 0:
                callout("warning", "Nilai per pesanan tinggi",
                        f"<b>{best.name}</b> peringkat #{int(best['rank_orders'])} dari sisi pesanan tetapi "
                        f"#{int(best['rank_revenue'])} dari sisi pendapatan — rata-rata "
                        f"{fmt_money(best['avg_price_per_item'])} per item. Promosi di sini berpotensi "
                        f"memberi pendapatan lebih besar per pesanan.")
    st.write("")

    # ---- Tabel --------------------------------------------------------------------
    with card():
        chart_title("Tabel lengkap kategori", "Dapat diurutkan dengan klik header kolom.")
        q = st.text_input("Cari kategori", placeholder="mis. health, furniture…", key="q2_search")
        table = cat.reset_index().rename(columns={
            "category_label": "Kategori", "revenue": "Pendapatan (R$)", "order_count": "Pesanan unik",
            "item_count": "Item terjual", "revenue_share_pct": "Kontribusi (%)",
            "rank_revenue": "Peringkat pendapatan", "rank_orders": "Peringkat pesanan",
            "avg_price_per_item": "Harga rata-rata/item (R$)", "revenue_per_order": "Pendapatan/pesanan (R$)"})
        if q:
            table = table[table["Kategori"].str.contains(q, case=False, na=False)]
        show_table(table, hide_index=True, height=420, column_config={
            "Pendapatan (R$)": st.column_config.NumberColumn(format="%.2f"),
            "Kontribusi (%)": st.column_config.ProgressColumn(format="%.2f%%", min_value=0,
                                                              max_value=float(max(cat["revenue_share_pct"].max(), 1))),
            "Harga rata-rata/item (R$)": st.column_config.NumberColumn(format="%.2f"),
            "Pendapatan/pesanan (R$)": st.column_config.NumberColumn(format="%.2f")})
        st.download_button("Unduh tabel (CSV)", cat.round(4).to_csv().encode("utf-8"),
                           file_name="ringkasan_kategori.csv", mime="text/csv", key="q2_dl")


def tab_conclusion(cat, rv):
    section("03", "Kesimpulan & Rekomendasi", "Kesimpulan dari notebook analisis, dilengkapi bukti dari periode terpilih.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with card():
            html(chip("Hasil notebook · Sep 2016 – Agu 2018", "archived"))
            html('<div class="ct" style="margin-top:6px">Kesimpulan pertanyaan 1</div>')
            st.markdown("Durasi keterlambatan pengiriman **sangat memengaruhi skor ulasan**. Semakin lama "
                        "pesanan terlambat, semakin rendah skor yang diberikan pelanggan. Meski begitu, "
                        "keterlambatan **bukan satu-satunya** penyebab skor ulasan rendah.")
            if len(rv) and (rv["delivery_status"] == STATUS_LATE).any():
                a = rv.loc[rv["delivery_status"] == STATUS_ONTIME, "review_score"].mean()
                b = rv.loc[rv["delivery_status"] == STATUS_LATE, "review_score"].mean()
                callout("success", "Bukti pada periode terpilih",
                        f"Skor rata-rata tepat waktu <b>{fmt_num(a)}</b> vs terlambat <b>{fmt_num(b)}</b>.")
    with c2:
        with card():
            html(chip("Hasil notebook · Sep 2016 – Agu 2018", "archived"))
            html('<div class="ct" style="margin-top:6px">Kesimpulan pertanyaan 2</div>')
            st.markdown("Kategori dengan pendapatan tertinggi adalah **health_beauty** dan terendah "
                        "**security_and_services**. Kategori dengan pendapatan tertinggi **belum tentu** "
                        "memiliki jumlah pesanan tertinggi — temuan ini menjadi dasar analisis lanjutan "
                        "untuk memaksimalkan promosi.")
            if len(cat):
                callout("success", "Bukti pada periode terpilih",
                        f"Tertinggi: <b>{cat.index[0]}</b> ({fmt_money(cat.iloc[0]['revenue'])}); "
                        f"terendah: <b>{cat.index[-1]}</b> ({fmt_money(cat.iloc[-1]['revenue'])}).")

    section("→", "Rekomendasi action item")
    a1, a2, a3 = st.columns(3, gap="large")
    items = [
        ("1", "Kurangi & kendalikan keterlambatan",
         "Prioritaskan pengiriman agar tidak melewati estimasi yang dijanjikan, terutama pesanan yang "
         "berisiko terlambat lebih dari 3 hari, karena skor ulasan jatuh tajam di rentang ini.", "red"),
        ("2", "Jaga kategori Top 5",
         "Kategori yang masuk Top 5 jumlah pesanan <i>dan</i> Top 5 pendapatan perlu diprioritaskan: "
         "jaga ketersediaan stok, pertahankan kualitas produk, dan jalankan promosi yang terbukti efektif.", "blue"),
        ("3", "Tinjau kategori berkinerja rendah",
         "Untuk kategori dengan pesanan dan pendapatan rendah, tinjau jumlah produk, frekuensi pesanan, "
         "harga, dan tren bulanan. Jika ada peningkatan, pertimbangkan promosi; jika tidak, tinjau ulang portofolio.", "yellow"),
    ]
    for col, (n, title, body, accent) in zip((a1, a2, a3), items):
        card_html = kpi_html(f"Aksi {n}", f'<span style="font-size:20px">{title}</span>',
                             f'<span style="color:#1F2937">{body}</span>', accent)
        col.markdown(card_html.replace('<div class="kpi ', '<div style="min-height:320px" class="kpi ', 1),
                     unsafe_allow_html=True)

    st.write("")
    callout("warning", "Catatan penafsiran",
            "Hubungan antara keterlambatan dan skor ulasan bersifat asosiatif, bukan bukti kausal. Pendapatan "
            "dihitung dari harga produk (tanpa ongkos kirim) pada pesanan berstatus <i>delivered</i>; "
            "skor ulasan per pesanan adalah rata-rata bila satu pesanan memiliki lebih dari satu ulasan.")


def tab_method(quality, delivery, sales):
    section("04", "Data & Metodologi", "Bagaimana angka pada dashboard ini dihitung.")
    m1, m2 = st.columns(2, gap="large")
    with m1:
        with card():
            chart_title("Definisi metrik")
            st.markdown(
                "- **Periode analisis:** pembelian 1 Sep 2016 – 31 Agu 2018\n"
                "- **Durasi pengiriman:** tanggal diterima pelanggan − tanggal pembelian (hari)\n"
                "- **Keterlambatan:** tanggal diterima − tanggal estimasi; **terlambat** bila > 0 hari\n"
                "- **Skor ulasan:** rata-rata `review_score` per pesanan; pesanan tanpa ulasan dikecualikan "
                "dari analisis skor tetapi tetap dihitung pada analisis pengiriman\n"
                "- **Pendapatan:** jumlah `price` item pada pesanan *delivered* (tanpa ongkir)\n"
                "- **Nama kategori:** terjemahan Inggris; bila tidak ada, memakai nama asli; "
                "produk tanpa kategori diberi label `unknown`")
    with m2:
        with card():
            chart_title("Alur pengolahan data")
            html("""
            <div class="step"><div class="step-n">1</div><div class="step-b"><b>Gathering</b> – 5 tabel: orders, order_reviews, order_items, products, category_translation.</div></div>
            <div class="step"><div class="step-n blue">2</div><div class="step-b"><b>Assessing</b> – cek missing value, duplikat, dan nilai tidak valid.</div></div>
            <div class="step"><div class="step-n">3</div><div class="step-b"><b>Cleaning</b> – kolom tanggal → datetime; kategori kosong → <i>unknown</i>.</div></div>
            <div class="step"><div class="step-n blue">4</div><div class="step-b"><b>EDA & visualisasi</b> – agregasi untuk dua pertanyaan bisnis, disajikan interaktif di dashboard ini.</div></div>""")
    st.write("")
    with card():
        chart_title("Ringkasan kualitas data", "Dihitung dari data mentah sebelum pembersihan.")
        show_table(quality, hide_index=True)
    st.write("")
    e1, e2 = st.columns(2, gap="large")
    with e1:
        with st.expander("Pratinjau data pengiriman (hasil olahan)"):
            show_table(delivery.head(100), hide_index=True)
    with e2:
        with st.expander("Pratinjau data penjualan per item (hasil olahan)"):
            show_table(sales.head(100), hide_index=True)


# =============================================================================
# 7. APLIKASI
# =============================================================================
def ensure_data() -> dict | None:
    """Kembalikan dict path CSV, atau tampilkan panel unggah bila belum ditemukan."""
    found = locate_csvs(st.session_state.get("upload_dir"))
    if len(found) == len(REQUIRED_FILES):
        return found
    missing = [REQUIRED_FILES[k] for k in REQUIRED_FILES if k not in found]
    html('<div class="hero"><div class="blob b1"></div><div class="blob b2"></div><div style="position:relative;z-index:2">'
         '<span class="badge">Proyek Analisis Data · E-Commerce Olist</span>'
         '<div class="hero-title">Olist E&#8209;Commerce Insights</div>'
         '<p class="hero-lead">Dataset belum ditemukan. Letakkan CSV di folder <b>data/</b> atau unggah di bawah ini.</p></div></div>')
    callout("warning", "File belum lengkap", "Belum ditemukan: " + ", ".join(f"<code>{m}</code>" for m in missing))
    files = st.file_uploader("Unggah ZIP dataset atau file CSV-nya", type=["zip", "csv"], accept_multiple_files=True)
    if files and st.button("Gunakan file ini", type="primary"):
        st.session_state["upload_dir"] = save_uploads(files)
        st.rerun()
    return None


def main() -> None:
    st.set_page_config(page_title="Olist E-Commerce Insights", page_icon="📦", layout="wide",
                       initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    _card_counter["n"] = 0

    found = ensure_data()
    if found is None:
        st.stop()
    data = load_data(tuple(sorted(found.items())))
    delivery, sales = data["delivery"], data["sales"]

    months = sorted(delivery["purchase_month"].unique())

    # ---- Sidebar ------------------------------------------------------------------
    with st.sidebar:
        html('<div class="brand"><div class="brand-logo">O</div><div><div class="brand-name">Olist Insights</div>'
             '<div class="brand-sub">Proyek Analisis Data</div></div></div>')
        st.divider()
        start_m, end_m = st.select_slider("Rentang bulan pembelian", options=months,
                                          value=(months[0], months[-1]), format_func=month_label)
        n_months = months.index(end_m) - months.index(start_m) + 1
        html(chip(f"{month_label(start_m)} → {month_label(end_m)}", "active") + chip(f"{n_months} bulan", "archived"))
        st.caption("Filter periode berlaku untuk seluruh tab. Pengaturan lain ada di dalam tiap tab.")
        st.divider()
        html('<div class="brand-sub">Sumber data: Olist E-Commerce Public Dataset.<br>'
             'Nilai uang dalam Real Brasil (R$).</div>')

    sel_months = [str(m) for m in pd.period_range(start_m, end_m, freq="M")]
    dv = delivery[delivery["purchase_month"].between(start_m, end_m)]
    valid = dv[dv["is_valid"]]
    rv = valid[valid["review_score"].notna()]
    sl = sales[sales["purchase_month"].between(start_m, end_m)]
    cat = category_table(sl) if len(sl) else pd.DataFrame()

    render_hero(len(dv), sl["price"].sum(),
                rv["review_score"].mean() if len(rv) else float("nan"),
                f"{month_label(start_m)} – {month_label(end_m)}")

    tabs = st.tabs(["Ringkasan", "Pengiriman & Ulasan", "Kategori Produk", "Kesimpulan", "Data & Metode"])
    with tabs[0]:
        tab_overview(dv, valid, rv, sl, cat, sel_months)
    with tabs[1]:
        tab_delivery(dv, valid, rv)
    with tabs[2]:
        tab_category(sl, cat, sel_months)
    with tabs[3]:
        tab_conclusion(cat, rv)
    with tabs[4]:
        tab_method(data["quality"], dv, sl)

    html('<div class="foot">Dibuat oleh <b>Annisa Nabila Putri</b> · Proyek Analisis Data E-Commerce · '
         'Dibangun dengan Streamlit &amp; Plotly · Tema: CreateSpace Design System</div>')


if __name__ == "__main__":
    main()
