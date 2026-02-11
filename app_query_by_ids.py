"""
Streamlit UI for querying MRL data by crop and pesticide IDs
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path


@st.cache_data
def load_reference_lists():
    """Load crops and pesticides reference lists"""
    crops_path = Path("output/crops.json")
    pesticides_path = Path("output/pesticides.json")

    with open(crops_path, 'r', encoding='utf-8') as f:
        crops = json.load(f)

    with open(pesticides_path, 'r', encoding='utf-8') as f:
        pesticides = json.load(f)

    return crops, pesticides


@st.cache_data
def load_mapped_datasets():
    """Load all mapped datasets"""
    datasets = {}

    # Load IL dataset
    il_path = Path("output/mapped_datasets/IL_He_with_ids.csv")
    if il_path.exists():
        datasets['IL'] = pd.read_csv(il_path, encoding='utf-8-sig')

    # Load EU dataset
    eu_path = Path("output/mapped_datasets/EU_with_ids.csv")
    if eu_path.exists():
        datasets['EU'] = pd.read_csv(eu_path, encoding='utf-8-sig', low_memory=False)

    # Load CODEX dataset
    codex_path = Path("output/mapped_datasets/CODEX_with_ids.csv")
    if codex_path.exists():
        datasets['CODEX'] = pd.read_csv(codex_path, encoding='utf-8-sig')

    return datasets


def query_data(crop_id, pesticide_id, datasets):
    """Query all datasets for matching crop and pesticide"""
    results = {}

    for dataset_name, df in datasets.items():
        # Convert to numeric for comparison (handles int, float, and string types)
        df_crop_ids = pd.to_numeric(df['crop_id_mapping'], errors='coerce')
        df_pesticide_ids = pd.to_numeric(df['pesticide_id_mapping'], errors='coerce')

        # Filter rows where crop_id_mapping and pesticide_id_mapping match
        mask = (df_crop_ids == crop_id) & (df_pesticide_ids == pesticide_id)
        filtered_df = df[mask].copy()

        if not filtered_df.empty:
            # Fix data types for display - convert to int where possible
            filtered_df['crop_id_mapping'] = df_crop_ids[mask].astype('Int64')
            filtered_df['pesticide_id_mapping'] = df_pesticide_ids[mask].astype('Int64')
            results[dataset_name] = filtered_df

    return results


# Page configuration
st.set_page_config(
    page_title="Query MRL Data by Crop and Pesticide",
    page_icon="🌾",
    layout="wide"
)

# Custom CSS for RTL
st.markdown("""
<style>
    .main, .block-container {
        direction: rtl;
        text-align: right;
    }

    .stSelectbox > div > div > div {
        direction: rtl;
        text-align: right;
    }

    h1, h2, h3 {
        text-align: right;
    }

    div[data-baseweb="popover"] [role="listbox"]{
        direction: rtl !important;
    }

    div[data-baseweb="popover"] [role="option"]{
        justify-content: flex-end !important;
        text-align: right !important;
    }

    .stSelectbox div[data-baseweb="select"] > div {
        flex-direction: row-reverse !important;
    }

    div[data-testid="stMarkdownContainer"] {
        direction: rtl !important;
        text-align: right !important;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown("# 🌾 מערכת שאילתות MRL לפי גידול וריסוס")
    st.markdown("---")

    # Load data
    with st.spinner("טוען נתונים..."):
        crops, pesticides = load_reference_lists()
        datasets = load_mapped_datasets()

    st.success(f"נטענו {len(crops)} גידולים, {len(pesticides)} ריסוסים, {len(datasets)} מערכי נתונים")

    # Create selection dropdowns
    col1, col2 = st.columns(2)

    with col1:
        # Crop selection
        crop_options = {f"{crop['name_he']} ({crop['name_en']})": crop['id'] for crop in crops}
        selected_crop_label = st.selectbox(
            "בחר גידול",
            options=[""] + list(crop_options.keys()),
            index=0
        )

    with col2:
        # Pesticide selection
        pesticide_options = {pest['name']: pest['id'] for pest in pesticides}
        selected_pesticide_label = st.selectbox(
            "בחר ריסוס",
            options=[""] + list(pesticide_options.keys()),
            index=0
        )

    st.markdown("---")

    # Show results when both are selected
    if selected_crop_label and selected_crop_label != "" and selected_pesticide_label and selected_pesticide_label != "":
        crop_id = crop_options[selected_crop_label]
        pesticide_id = pesticide_options[selected_pesticide_label]

        with st.spinner("מחפש נתונים..."):
            results = query_data(crop_id, pesticide_id, datasets)

        if not results:
            st.warning("לא נמצאו נתונים עבור הצירוף הזה")
        else:
            st.success(f"נמצאו תוצאות ב-{len(results)} מערכי נתונים")

            # Create tabs for each dataset
            tabs = st.tabs([f"🌍 {name}" for name in results.keys()])

            for idx, (dataset_name, df) in enumerate(results.items()):
                with tabs[idx]:
                    st.markdown(f"### {dataset_name} - {len(df)} שורות")
                    st.dataframe(df, width='stretch', hide_index=True)


if __name__ == "__main__":
    main()
