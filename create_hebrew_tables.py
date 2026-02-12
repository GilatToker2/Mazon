"""
Create Hebrew-translated CSV files with RTL column order
"""

import pandas as pd
from pathlib import Path


# The 6 new mapping columns that were added
MAPPING_COLUMNS = [
    'crop_id_mapping',
    'crop_name_mapping',
    'crop_reasoning',
    'pesticide_id_mapping',
    'pesticide_name_mapping',
    'pesticide_reasoning'
]

# Translation for the 6 mapping columns (same for all datasets)
MAPPING_TRANSLATIONS = {
    'crop_id_mapping': 'מזהה גידול ממופה',
    'crop_name_mapping': 'שם גידול ממופה',
    'crop_reasoning': 'הסבר מיפוי גידול',
    'pesticide_id_mapping': 'מזהה חומר הדברה ממופה',
    'pesticide_name_mapping': 'שם חומר הדברה ממופה',
    'pesticide_reasoning': 'הסבר מיפוי חומר הדברה'
}

# Translation mappings for each dataset
EU_TRANSLATIONS = {
    'Crop_ID': 'מזהה גידול',
    'Crop': 'גידול',
    'Pesticide': 'חומר הדברה',
    'MRL_Limit_mg_kg': 'MRL (מג"ק לק"ג)',
    'Is_LOD': 'גבול זיהוי',
    'Valid_From': 'תקף מתאריך',
    'Notes': 'הערות',
    'Pesticide_Original_EU': 'שם מקורי EU',
    **MAPPING_TRANSLATIONS
}

CODEX_TRANSLATIONS = {
    'Commodity_Name': 'שם מוצר',
    'Commodity_Code': 'קוד מוצר',
    'Pesticide_Name': 'שם חומר הדברה',
    'MRL_Value': 'ערך MRL',
    'Flag_Po_Fat': 'דגל שומן',
    'Year_Legal_CAC': 'שנה משפטית CAC',
    'Full_Notes': 'הערות מלאות',
    'Year_Science_JMPR': 'שנה מדעית JMPR',
    'Flag_Status': 'סטטוס',
    'Is_LOD': 'גבול זיהוי',
    'Commodity_ID': 'מזהה מוצר',
    'Pesticide_ID': 'מזהה חומר הדברה',
    **MAPPING_TRANSLATIONS
}

# For IL_He dataset - columns are already in Hebrew, just translate the 6 new mapping columns
IL_TRANSLATIONS = {
    **MAPPING_TRANSLATIONS
}

US_TRANSLATIONS = {
    'Crop': 'גידול',
    'Pesticide': 'חומר הדברה',
    'MRL': 'MRL (PPM)',
    'Source': 'מקור',
    **MAPPING_TRANSLATIONS
}


def translate_and_reverse_columns(df, translation_dict):
    """
    Translate column names to Hebrew. Keep original columns in same order,
    with the 6 mapping columns at the end (left side).
    """
    # First, identify which mapping columns exist in the original dataframe
    original_columns = list(df.columns)
    mapping_cols_in_df = [col for col in original_columns if col in MAPPING_COLUMNS]
    original_cols_in_df = [col for col in original_columns if col not in MAPPING_COLUMNS]

    # Keep original columns in same order, add mapping columns at the end
    new_column_order = original_cols_in_df + mapping_cols_in_df

    # Reorder the dataframe
    df_reordered = df[new_column_order]

    # Now translate column names
    df_translated = df_reordered.rename(columns=translation_dict)

    return df_translated


def create_hebrew_csv(input_path, output_path, translation_dict):
    """
    Read CSV, translate columns, reverse order, and save as new file
    """
    print(f"Processing {input_path.name}...")

    # Read the original CSV
    df = pd.read_csv(input_path, encoding='utf-8-sig', low_memory=False)

    # Translate and reverse columns
    df_hebrew = translate_and_reverse_columns(df, translation_dict)

    # Save with Hebrew BOM for proper encoding
    df_hebrew.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"✓ Created {output_path.name} with {len(df_hebrew)} rows and {len(df_hebrew.columns)} columns")
    print(f"  Columns (RTL order): {', '.join(df_hebrew.columns[:5])}...")


def main():
    """Create Hebrew versions of IL, EU and CODEX datasets"""

    output_dir = Path("output/mapped_datasets")

    # Process IL_He dataset (already Hebrew, just translate 6 new mapping columns)
    il_input = output_dir / "IL_He_with_ids.csv"
    il_output = output_dir / "IL_He_with_ids_he.csv"

    if il_input.exists():
        create_hebrew_csv(il_input, il_output, IL_TRANSLATIONS)
    else:
        print(f"⚠ Warning: {il_input} not found")

    print()

    # Process EU dataset
    eu_input = output_dir / "EU_with_ids.csv"
    eu_output = output_dir / "EU_with_ids_he.csv"

    if eu_input.exists():
        create_hebrew_csv(eu_input, eu_output, EU_TRANSLATIONS)
    else:
        print(f"⚠ Warning: {eu_input} not found")

    print()

    # Process CODEX dataset
    codex_input = output_dir / "CODEX_with_ids.csv"
    codex_output = output_dir / "CODEX_with_ids_he.csv"

    if codex_input.exists():
        create_hebrew_csv(codex_input, codex_output, CODEX_TRANSLATIONS)
    else:
        print(f"⚠ Warning: {codex_input} not found")

    print()

    # Process US dataset
    us_input = output_dir / "US_with_ids.csv"
    us_output = output_dir / "US_with_ids_he.csv"

    if us_input.exists():
        create_hebrew_csv(us_input, us_output, US_TRANSLATIONS)
    else:
        print(f"⚠ Warning: {us_input} not found")

    print("\n✅ Hebrew CSV files created successfully!")
    print("   Files are saved with RTL column order and Hebrew column names")
    print("   Original columns: Right-to-Left | Mapping columns: On the left")


if __name__ == "__main__":
    main()
