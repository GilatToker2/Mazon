"""
Ministry of Health MRL Comparison Dashboard - Integrated Version
Combines Beautiful UI Design with Real Data Loading
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
from pathlib import Path


# ============================================================================
# DATA LOADING FUNCTIONS (FROM ORIGINAL)
# ============================================================================

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
    """Load all mapped datasets (Hebrew versions)"""
    datasets = {}

    # Load IL dataset (Hebrew)
    il_path = Path("output/mapped_datasets/IL_He_with_ids_he.csv")
    if il_path.exists():
        datasets['IL'] = pd.read_csv(il_path, encoding='utf-8-sig')

    # Load EU dataset (Hebrew)
    eu_path = Path("output/mapped_datasets/EU_with_ids_he.csv")
    if eu_path.exists():
        datasets['EU'] = pd.read_csv(eu_path, encoding='utf-8-sig', low_memory=False)

    # Load CODEX dataset (Hebrew)
    codex_path = Path("output/mapped_datasets/CODEX_with_ids_he.csv")
    if codex_path.exists():
        datasets['CODEX'] = pd.read_csv(codex_path, encoding='utf-8-sig')

    # Load US dataset (Hebrew)
    us_path = Path("output/mapped_datasets/US_with_ids_he.csv")
    if us_path.exists():
        datasets['US'] = pd.read_csv(us_path, encoding='utf-8-sig')

    return datasets


def check_id_match(value, target_id):
    """בדוק אם value מכיל את target_id (יכול להיות ערך בודד או רשימת JSON)"""
    if pd.isna(value):
        return False

    # אם זה מחרוזת שמתחילה ב-[ זו רשימת JSON
    if isinstance(value, str) and value.strip().startswith('['):
        try:
            id_list = json.loads(value)
            return target_id in id_list
        except:
            pass

    # אחרת, נסה להשוות כמספר
    try:
        return float(value) == target_id
    except:
        return False


def query_data(crop_id, pesticide_id, datasets):
    """Query all datasets for matching crop and pesticide"""
    results = {}

    # Hebrew column names for the mapping columns
    crop_id_col = 'מזהה גידול ממופה'
    pesticide_id_col = 'מזהה חומר הדברה ממופה'

    for dataset_name, df in datasets.items():
        # השתמש ב-apply לבדוק כל ערך בעמודה
        crop_mask = df[crop_id_col].apply(lambda x: check_id_match(x, crop_id))
        pesticide_mask = df[pesticide_id_col].apply(lambda x: check_id_match(x, pesticide_id))

        # שלב את שתי המסכות
        mask = crop_mask & pesticide_mask
        filtered_df = df[mask].copy()

        if not filtered_df.empty:
            results[dataset_name] = filtered_df

    return results


def generate_region_card_html(region_name, region_class, flag, icon, df):
    """Generate HTML for a region card with actual data"""

    # Determine column names based on region
    if region_name == "IL":
        display_name = "ישראל"
        # Hebrew columns from IL dataset
        pesticide_col = 'שם חומר הדברה'  # or the actual column name
        crop_col = 'שם גידול'
        mrl_col = 'MRL'  # Update with actual column name
        date_col = 'תאריך עדכון'  # Update with actual column name
    elif region_name == "EU":
        display_name = "איחוד אירופי"
        pesticide_col = 'Pesticide'  # Update with actual column names
        crop_col = 'Crop'
        mrl_col = 'MRL'
        date_col = 'Date'
    elif region_name == "CODEX":
        display_name = "קודקס"
        pesticide_col = 'Pesticide'
        crop_col = 'Crop'
        mrl_col = 'MRL'
        date_col = 'Date'
    else:
        display_name = region_name
        pesticide_col = crop_col = mrl_col = date_col = None

    # Build table rows
    rows_html = ""
    for idx, row in df.iterrows():
        # Try to extract values safely
        try:
            pesticide_val = row.get(pesticide_col, "N/A") if pesticide_col in row else "N/A"
            crop_val = row.get(crop_col, "N/A") if crop_col in row else "N/A"
            mrl_val = row.get(mrl_col, "N/A") if mrl_col in row else "N/A"
            date_val = row.get(date_col, "N/A") if date_col in row else "N/A"
        except:
            # Fallback to first columns
            cols = list(row.index)
            pesticide_val = row[cols[0]] if len(cols) > 0 else "N/A"
            crop_val = row[cols[1]] if len(cols) > 1 else "N/A"
            mrl_val = row[cols[2]] if len(cols) > 2 else "N/A"
            date_val = row[cols[3]] if len(cols) > 3 else "N/A"

        rows_html += f"""
        <tr>
            <td><span class="date-badge">{date_val}</span></td>
            <td><span class="mrl-value">{mrl_val}</span></td>
            <td>
                <div class="crop-name">{crop_val}</div>
            </td>
            <td>
                <div class="pesticide-name">{pesticide_val}</div>
            </td>
        </tr>
        """

    card_html = f"""
    <div class="region-card {region_class}">
        <div class="region-card-header">
            <div class="region-card-header-left">
                <span class="region-flag">{flag}</span>
                <h3 class="region-name">{display_name}</h3>
            </div>
            <span class="region-icon">{icon}</span>
        </div>
        <div class="region-card-body">
            <table class="region-table">
                <thead>
                    <tr>
                        <th>תאריך עדכון</th>
                        <th>רמת MRL</th>
                        <th>גידול</th>
                        <th>חומר הדברה</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>
    """
    return card_html


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Ministry of Health - MRL Comparison Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# COMPREHENSIVE CSS STYLING
# ============================================================================

st.markdown("""
<style>
    /* ===== GOOGLE FONT IMPORT ===== */
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700&display=swap');

    /* ===== GLOBAL RESET & RTL ===== */
    * {
        font-family: 'Heebo', sans-serif;
    }

    html, body, [class*="css"] {
        direction: rtl;
        text-align: right;
    }

    /* ===== REMOVE STREAMLIT DEFAULTS ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #f8fafc;
    }

    .block-container {
        padding-top: 0rem !important;
        padding-right: 1rem !important;
        padding-left: 1rem !important;
        max-width: 100% !important;
    }

    /* ===== CUSTOM HEADER COMPONENT ===== */
    .moh-header {
        background: white;
        border-bottom: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        padding: 1rem 2rem;
        margin: -1rem -1rem 2rem -1rem;
        position: sticky;
        top: 0;
        z-index: 999;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .moh-header-right {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .moh-logo {
        height: 60px;
        width: auto;
        object-fit: contain;
    }

    .moh-header-center {
        flex: 1;
        text-align: center;
    }

    .moh-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
        display: inline-block;
    }

    .moh-badge {
        display: inline-block;
        background: linear-gradient(135deg, #e11d48 0%, #f43f5e 100%);
        color: white;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        margin-right: 0.5rem;
        box-shadow: 0 2px 4px rgba(225, 29, 72, 0.3);
    }

    .moh-header-left {
        display: flex;
        align-items: center;
    }

    .kpmg-logo {
        height: 40px;
        width: auto;
        object-fit: contain;
    }

    /* ===== FILTER CARD COMPONENT ===== */
    .filter-card {
        background: white;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        padding: 2rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }

    .filter-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #0056b3 0%, #2e7d32 100%);
    }

    .filter-card-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0 0 1.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .filter-card-icon {
        font-size: 1.5rem;
    }

    /* ===== STREAMLIT SELECT BOX STYLING ===== */
    .stSelectbox {
        direction: rtl;
    }

    .stSelectbox > div > div > div {
        direction: rtl;
        text-align: right;
        border-radius: 8px;
        border-color: #cbd5e1;
        transition: all 0.2s;
    }

    .stSelectbox > div > div > div:hover {
        border-color: #0056b3;
    }

    .stSelectbox > div > div > div:focus-within {
        border-color: #0056b3;
        box-shadow: 0 0 0 3px rgba(0, 86, 179, 0.1);
    }

    div[data-baseweb="select"] > div {
        flex-direction: row-reverse !important;
        background-color: #f8fafc;
    }

    div[data-baseweb="popover"] [role="listbox"]{
        direction: rtl !important;
        border-radius: 8px;
    }

    div[data-baseweb="popover"] [role="option"]{
        justify-content: flex-end !important;
        text-align: right !important;
        transition: background-color 0.15s;
    }

    div[data-baseweb="popover"] [role="option"]:hover{
        background-color: #eff6ff !important;
    }

    /* ===== CUSTOM BUTTON STYLING ===== */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #0056b3 0%, #003d82 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 4px 6px -1px rgba(0, 86, 179, 0.2);
        direction: rtl;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #003d82 0%, #002b5c 100%);
        transform: scale(0.98);
        box-shadow: 0 2px 4px -1px rgba(0, 86, 179, 0.3);
    }

    .stButton > button:active {
        transform: scale(0.96);
    }

    /* ===== REGION CARDS GRID ===== */
    .results-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
        gap: 1.5rem;
        margin-top: 2rem;
    }

    @media (max-width: 1200px) {
        .results-grid {
            grid-template-columns: 1fr;
        }
    }

    /* ===== REGION CARD BASE ===== */
    .region-card {
        background: white;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        overflow: hidden;
        transition: all 0.3s;
    }

    .region-card:hover {
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        transform: translateY(-2px);
    }

    /* ===== REGION CARD HEADERS ===== */
    .region-card-header {
        padding: 1rem 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #e2e8f0;
    }

    .region-card-header-left {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .region-flag {
        font-size: 1.75rem;
    }

    .region-name {
        font-size: 1.125rem;
        font-weight: 700;
        margin: 0;
    }

    .region-icon {
        font-size: 1.25rem;
        opacity: 0.7;
    }

    /* Region-specific header colors */
    .region-card.israel .region-card-header {
        background-color: #dbeafe;
    }

    .region-card.israel .region-name {
        color: #0056b3;
    }

    .region-card.eu .region-card-header {
        background-color: #e0e7ff;
    }

    .region-card.eu .region-name {
        color: #4f46e5;
    }

    .region-card.usa .region-card-header {
        background-color: #d1fae5;
    }

    .region-card.usa .region-name {
        color: #059669;
    }

    .region-card.codex .region-card-header {
        background-color: #ccfbf1;
    }

    .region-card.codex .region-name {
        color: #0891b2;
    }

    /* ===== REGION TABLE STYLING ===== */
    .region-card-body {
        padding: 0;
    }

    .region-table {
        width: 100%;
        border-collapse: collapse;
    }

    .region-table thead {
        background-color: #f8fafc;
        border-bottom: 2px solid #e2e8f0;
    }

    .region-table th {
        padding: 0.75rem 1rem;
        text-align: right;
        font-size: 0.875rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }

    .region-table tbody tr {
        border-bottom: 1px solid #f1f5f9;
        transition: background-color 0.15s;
    }

    .region-table tbody tr:hover {
        background-color: #f8fafc;
    }

    .region-table tbody tr:last-child {
        border-bottom: none;
    }

    .region-table td {
        padding: 1rem;
        text-align: right;
        font-size: 0.9375rem;
    }

    /* ===== TABLE CELL CONTENT STYLING ===== */
    .pesticide-name {
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.25rem;
    }

    .pesticide-name-en {
        font-size: 0.8125rem;
        color: #94a3b8;
        font-weight: 400;
    }

    .crop-name {
        font-weight: 500;
        color: #334155;
        margin-bottom: 0.25rem;
    }

    .crop-name-en {
        font-size: 0.8125rem;
        color: #94a3b8;
        font-weight: 400;
    }

    .mrl-value {
        font-weight: 700;
        font-family: 'Courier New', monospace;
        color: #0f172a;
        font-size: 1rem;
    }

    .date-badge {
        display: inline-block;
        background-color: #f1f5f9;
        color: #64748b;
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: 500;
    }

    .confidence-badge {
        display: inline-block;
        background-color: #fef3c7;
        color: #d97706;
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: 600;
        border: 1px solid #fde68a;
    }

    /* ===== EMPTY STATE ===== */
    .empty-state {
        text-align: center;
        padding: 3rem 2rem;
        color: #94a3b8;
    }

    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }

    .empty-state-text {
        font-size: 1.125rem;
        font-weight: 500;
        color: #64748b;
    }

    /* ===== STATUS MESSAGES ===== */
    .stAlert {
        direction: rtl;
        border-radius: 8px;
    }

    /* ===== LOADING SPINNER ===== */
    .stSpinner > div {
        border-top-color: #0056b3 !important;
    }

    /* ===== RESPONSIVE ADJUSTMENTS ===== */
    @media (max-width: 768px) {
        .moh-header {
            flex-direction: column;
            gap: 1rem;
            padding: 1rem;
        }

        .moh-title {
            font-size: 1.25rem;
        }

        .filter-card {
            padding: 1.5rem;
        }

        .region-table th,
        .region-table td {
            padding: 0.5rem;
            font-size: 0.875rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CUSTOM HEADER COMPONENT
# ============================================================================

# Create header with Streamlit columns
header_cols = st.columns([1, 3, 1])

with header_cols[0]:
    st.image("Img/health.png", width=200)

with header_cols[1]:
    st.markdown("""
    <div style="text-align: center; padding-top: 10px;">
        <h1 style="font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0;">
            <span style="display: inline-block; background: linear-gradient(135deg, #e11d48 0%, #f43f5e 100%); color: white; font-size: 0.75rem; font-weight: 600; padding: 0.25rem 0.75rem; border-radius: 9999px; margin-left: 0.5rem; box-shadow: 0 2px 4px rgba(225, 29, 72, 0.3);">POC Version</span>
            מערכת השוואת רמות MRL
        </h1>
    </div>
    """, unsafe_allow_html=True)

with header_cols[2]:
    st.image("Img/kpmg.jpg", width=120)

st.markdown("<hr style='margin: 1rem 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

# ============================================================================
# LOAD DATA
# ============================================================================

crops, pesticides = load_reference_lists()
datasets = load_mapped_datasets()

# ============================================================================
# FILTER SECTION (STYLED CARD)
# ============================================================================

st.markdown("""
<div class="filter-card">
    <h2 class="filter-card-title">
        <span class="filter-card-icon">🔍</span>
        בחר גידול וחומר הדברה
    </h2>
</div>
""", unsafe_allow_html=True)

# Use negative margin to place inputs inside the card visually
st.markdown('<div style="margin-top: -1rem;">', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    # Load actual crop options
    crop_options = {f"{crop['name_he']} ({crop['name_en']})": crop['id'] for crop in crops}
    selected_crop_label = st.selectbox(
        "בחר גידול",
        options=[""] + list(crop_options.keys()),
        index=0,
        key="crop_selector"
    )

with col2:
    # Load actual pesticide options
    pesticide_options = {pest['name']: pest['id'] for pest in pesticides}
    selected_pesticide_label = st.selectbox(
        "בחר חומר הדברה",
        options=[""] + list(pesticide_options.keys()),
        index=0,
        key="pesticide_selector"
    )

st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# RESULTS GRID SECTION WITH REAL DATA
# ============================================================================

# Automatically show results when both selections are made
if selected_crop_label and selected_crop_label != "" and selected_pesticide_label and selected_pesticide_label != "":

    crop_id = crop_options[selected_crop_label]
    pesticide_id = pesticide_options[selected_pesticide_label]

    with st.spinner("מחפש נתונים..."):
        results = query_data(crop_id, pesticide_id, datasets)

    if not results:
        st.warning("⚠️ לא נמצאו נתונים עבור הצירוף הזה")
    else:
        st.success(f"✅ נמצאו תוצאות ב-{len(results)} מערכי נתונים")

        st.markdown("---")

        # Map dataset names to display configuration
        region_config = {
            'IL': {'class': 'israel', 'flag': '🇮🇱', 'icon': '📋', 'name': 'ישראל'},
            'EU': {'class': 'eu', 'flag': '🇪🇺', 'icon': '🌍', 'name': 'איחוד אירופי'},
            'CODEX': {'class': 'codex', 'flag': '🌐', 'icon': '📊', 'name': 'קודקס'},
            'US': {'class': 'usa', 'flag': '🇺🇸', 'icon': '🗽', 'name': 'ארצות הברית'}
        }

        # Start results grid
        st.markdown('<div class="results-grid">', unsafe_allow_html=True)

        # Generate cards for each result
        for dataset_name, df in results.items():
            config = region_config.get(dataset_name, {
                'class': 'israel',
                'flag': '🌍',
                'icon': '📊',
                'name': dataset_name
            })

            # Use st.dataframe for better data display (from original code)
            st.markdown(f"""
            <div class="region-card {config['class']}">
                <div class="region-card-header">
                    <div class="region-card-header-left">
                        <span class="region-flag">{config['flag']}</span>
                        <h3 class="region-name">{config['name']}</h3>
                    </div>
                    <span class="region-icon">{config['icon']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Display dataframe with RTL support (from original approach)
            # Reverse column order for RTL
            df_display = df[df.columns[::-1]]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Scroll to results
        components.html("""
            <script>
            setTimeout(function() {
                window.parent.scrollTo(0, 500);
            }, 100);
            </script>
        """, height=0)

else:
    # Empty state before search
    st.markdown("""
    <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <div class="empty-state-text">בחר גידול וחומר הדברה</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94a3b8; font-size: 0.875rem; padding: 1rem;">
    <p>מערכת POC לצורך הדגמה בלבד | פותח עבור משרד הבריאות | © 2026 KPMG</p>
</div>
""", unsafe_allow_html=True)
