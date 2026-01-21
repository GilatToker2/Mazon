"""
Streamlit UI for Crop Pesticide Data Query System
This interface allows users to search for crop pesticide data in Hebrew
and view results from IL, EU, and US regulatory mechanisms.
"""

import streamlit as st
import pandas as pd
import json
from query_crop_data import query_crop_data, load_mapping


def get_all_hebrew_crops():
    """Extract all Hebrew crop names from the mapping for the dropdown"""
    mapping = load_mapping()
    crops = mapping.get('crops', {})

    # Filter only Hebrew names (keys that contain Hebrew characters)
    hebrew_crops = []
    for key in crops.keys():
        # Check if key contains Hebrew characters (Unicode range 0x0590-0x05FF)
        if isinstance(key, str) and any('\u0590' <= c <= '\u05FF' for c in key):
            hebrew_crops.append(key)

    return sorted(hebrew_crops)


# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="מערכת בירור נתוני חומרי הדברה",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for RTL and better styling
st.markdown("""
<style>
    /* RTL Support */
    .main, .block-container {
        direction: rtl;
        text-align: right;
    }

    /* Fix input fields to be RTL */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stMultiSelect > div > div > div {
        direction: rtl;
        text-align: right;
    }

    /* Style the search button */
    .stButton > button {
        width: 100%;
        background-color: #FF6B35;
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 8px;
        padding: 12px;
        border: none;
    }

    .stButton > button:hover {
        background-color: #E85A2A;
        border: none;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: flex-end;
    }

    /* DataFrame styling */
    .dataframe {
        direction: rtl;
    }

    /* Title styling */
    h1, h2, h3 {
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_hebrew_crops():
    """Load and cache Hebrew crop names"""
    return get_all_hebrew_crops()


def main():
    # Title and description
    st.markdown("# 🌾 מערכת בירור נתוני חומרי הדברה לגידולים")
    st.markdown(
        """
        <div dir="rtl" style="text-align: right;">
            חפשו גידול בעברית וקבלו את נתוני הגבלות חומרי ההדברה לפי מנגנוני הרגולציה:
            <ul>
                <li><b>ישראל (IL)</b></li>
                <li><b>האיחוד האירופי (EU)</b></li>
                <li><b>ארצות הברית (US)</b></li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # Load crop names
    with st.spinner("טוען רשימת גידולים..."):
        hebrew_crops = load_hebrew_crops()

    # Create two columns for input - search button on left side
    col1, col2 = st.columns([4, 1])

    with col1:
        # Selectbox with search capability
        selected_crop = st.selectbox(
            "בחר גידול מהרשימה או התחל להקליד לחיפוש",
            options=[""] + hebrew_crops,
            index=0,
            help=f"סה\"כ {len(hebrew_crops)} גידולים זמינים. התחל להקליד לסינון הרשימה."
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        search_clicked = st.button("🔍 חפש", type="primary", use_container_width=True)

    # Add some spacing
    st.markdown("<br>", unsafe_allow_html=True)

    # Show search results when crop is selected or button is clicked
    if selected_crop and selected_crop != "":
        with st.spinner(f"מחפש נתונים עבור: {selected_crop}..."):
            try:
                # Query the crop data
                il_table, eu_table, us_table = query_crop_data(selected_crop)

                # Check if any table has data
                has_data = False
                for table in [il_table, eu_table, us_table]:
                    if table is not None and len(table.columns) > 3:
                        has_data = True
                        break

                # Status message
                if not has_data:
                    st.success(f"✅ נמצא: {selected_crop}")
                    st.warning("❌ אין הגבלות חומרי הדברה עבור גידול זה (IL, EU, US)")
                else:
                    # Count pesticides
                    il_count = len(il_table.columns) - 3 if il_table is not None and len(il_table.columns) > 3 else 0
                    eu_count = len(eu_table.columns) - 3 if eu_table is not None and len(eu_table.columns) > 3 else 0
                    us_count = len(us_table.columns) - 3 if us_table is not None and len(us_table.columns) > 3 else 0

                    st.success(f"✅ נמצא: {selected_crop}")

                    # Display counts in columns
                    metric_col1, metric_col2, metric_col3 = st.columns(3)
                    with metric_col3:  # Reversed order for RTL
                        st.metric("🇮🇱 ישראל (IL)", f"{il_count} חומרי הדברה")
                    with metric_col2:
                        st.metric("🇪🇺 האיחוד האירופי (EU)", f"{eu_count} חומרי הדברה")
                    with metric_col1:
                        st.metric("🇺🇸 ארצות הברית (US)", f"{us_count} חומרי הדברה")

                st.markdown("---")
                st.markdown("## 📋 תוצאות")

                # Create tabs for each mechanism
                tab1, tab2, tab3 = st.tabs(["🇮🇱 ישראל (IL)", "🇪🇺 האיחוד האירופי (EU)", "🇺🇸 ארצות הברית (US)"])

                with tab1:
                    if il_table is not None and len(il_table.columns) > 3:
                        st.markdown(f"**נמצאו {len(il_table.columns) - 3} חומרי הדברה**")
                        st.dataframe(il_table, use_container_width=True, hide_index=True)

                        # Download button
                        csv = il_table.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="💾 הורד כקובץ CSV",
                            data=csv,
                            file_name=f"IL_{selected_crop.replace(' ', '_')}.csv",
                            mime="text/csv",
                        )
                    else:
                        st.info("אין נתונים זמינים עבור מנגנון IL")

                with tab2:
                    if eu_table is not None and len(eu_table.columns) > 3:
                        st.markdown(f"**נמצאו {len(eu_table.columns) - 3} חומרי הדברה**")
                        st.dataframe(eu_table, use_container_width=True, hide_index=True)

                        # Download button
                        csv = eu_table.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="💾 הורד כקובץ CSV",
                            data=csv,
                            file_name=f"EU_{selected_crop.replace(' ', '_')}.csv",
                            mime="text/csv",
                        )
                    else:
                        st.info("אין נתונים זמינים עבור מנגנון EU")

                with tab3:
                    if us_table is not None and len(us_table.columns) > 3:
                        st.markdown(f"**נמצאו {len(us_table.columns) - 3} חומרי הדברה**")
                        st.dataframe(us_table, use_container_width=True, hide_index=True)

                        # Download button
                        csv = us_table.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="💾 הורד כקובץ CSV",
                            data=csv,
                            file_name=f"US_{selected_crop.replace(' ', '_')}.csv",
                            mime="text/csv",
                        )
                    else:
                        st.info("אין נתונים זמינים עבור מנגנון US")

            except Exception as e:
                st.error(f"❌ שגיאה: {str(e)}")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div dir="rtl" style="text-align: right;">
            <p><b>הערות:</b></p>
            <ul>
                <li>התחל להקליד בתיבת הבחירה כדי לסנן את רשימת הגידולים</li>
                <li>הטבלאות ניתנות להורדה ישירות מכל טאב</li>
                <li>הנתונים מבוססים על מנגנוני רגולציה: ישראל (IL), האיחוד האירופי (EU), ארצות הברית (US)</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
