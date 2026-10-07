from pathlib import Path

import joblib
import pandas as pd
import streamlit as st
import trafilatura

st.set_page_config(page_title="Klasifikasi Berita", page_icon="📰", layout="wide")


@st.cache_resource
def load_model():
    # Path relatif terhadap lokasi app.py, supaya jalan di komputer maupun di Streamlit Cloud
    model_path = Path(__file__).parent / "model_berita.pkl"
    return joblib.load(model_path)


@st.cache_data(show_spinner=False)
def ambil_berita(url: str):
    """Ambil judul & isi berita dari sebuah link."""
    html = trafilatura.fetch_url(url)
    if not html:
        return None, None
    teks = trafilatura.extract(html, include_comments=False, include_tables=False)
    meta = trafilatura.extract_metadata(html)
    judul = meta.title if meta and meta.title else "(Judul tidak ditemukan)"
    return judul, teks


model = load_model()

st.title("📰 Aplikasi Klasifikasi Berita")
st.caption("Tempel link berita, lalu model Naive Bayes akan menentukan kategorinya.")

tab_link, tab_teks = st.tabs(["🔗 Dari Link", "✍️ Tempel Teks"])

judul, teks = None, None

with tab_link:
    url = st.text_input("Masukkan link berita", placeholder="https://www.contoh.com/berita/...")
    if st.button("Klasifikasikan", type="primary", key="btn_link"):
        if not url.strip():
            st.warning("Link belum diisi.")
        else:
            with st.spinner("Mengambil berita..."):
                judul, teks = ambil_berita(url.strip())
            if not teks:
                st.error("Gagal mengambil isi berita. Coba link lain, atau gunakan tab 'Tempel Teks'.")

with tab_teks:
    teks_manual = st.text_area("Tempel isi berita", height=250)
    if st.button("Klasifikasikan", type="primary", key="btn_teks"):
        if teks_manual.strip():
            judul, teks = "Teks manual", teks_manual.strip()
        else:
            st.warning("Teks belum diisi.")

# ---- Hasil ----
if teks:
    # Samakan dengan training: teks model = judul + isi berita
    judul_model = "" if judul in (None, "Teks manual", "(Judul tidak ditemukan)") else judul
    teks_model = f"{judul_model} {teks}".strip()

    prediksi = model.predict([teks_model])[0]
    proba = model.predict_proba([teks_model])[0]
    df_proba = (
        pd.DataFrame({"Kategori": model.classes_, "Probabilitas": proba})
        .sort_values("Probabilitas", ascending=False)
        .reset_index(drop=True)
    )

    st.divider()
    kol_berita, kol_hasil = st.columns([3, 2])

    with kol_berita:
        st.subheader(judul)
        st.write(teks)

    with kol_hasil:
        st.subheader("Hasil Klasifikasi")
        st.success(f"Kategori: **{prediksi}**")
        st.metric("Keyakinan", f"{df_proba.loc[0, 'Probabilitas'] * 100:.1f}%")
        st.bar_chart(df_proba.set_index("Kategori"))
        st.dataframe(
            df_proba.style.format({"Probabilitas": "{:.2%}"}),
            hide_index=True,
            use_container_width=True,
        )