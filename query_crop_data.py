import pandas as pd
import json
import sys


def load_mapping():
    """Load the golden mapping JSON file"""
    try:
        with open('golden_mapping_expanded.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: golden_mapping_expanded.json not found.")
        sys.exit(1)


def get_crop_id(mapping, hebrew_word):
    """Get CROP_ID(s) from Hebrew word using the mapping.
    Returns a list of crop_ids and a list of crop_info dictionaries."""
    crops = mapping['crops']

    # Search for the Hebrew word in the crops mapping
    if hebrew_word in crops:
        crop_id_value = crops[hebrew_word]

        # Handle both single ID and list of IDs
        if isinstance(crop_id_value, list):
            # Multiple IDs for this Hebrew word
            crop_ids = crop_id_value
        elif isinstance(crop_id_value, int):
            # Single ID
            crop_ids = [crop_id_value]
        else:
            return None, None

        # Get crop info for all IDs
        crop_infos = []
        for cid in crop_ids:
            if str(cid) in crops:
                crop_infos.append(crops[str(cid)])

        return crop_ids, crop_infos

    return None, None


def get_non_empty_columns(df, crop_id, crop_column_name):
    """Get all columns with non-empty values for a specific crop"""
    # Find the row for this crop by Crop_ID
    crop_row = df[df[crop_column_name] == crop_id]

    if crop_row.empty:
        return []

    # Get the first matching row
    row = crop_row.iloc[0]

    # Find all columns with non-empty values (not NaN and not empty string)
    # Skip metadata columns: Crop_ID, Crop_Map_Name, Crop_Data_Name
    non_empty_cols = []
    skip_columns = ['Crop_ID', 'Crop_Map_Name', 'Crop_Data_Name']

    for col in df.columns:
        if col in skip_columns:
            continue
        value = row[col]
        if pd.notna(value) and str(value).strip() != '':
            non_empty_cols.append(col)

    return non_empty_cols


def create_pesticide_tables_by_mechanism(crop_ids, crop_infos):
    """Create 3 separate tables - one for each mechanism (IL, EU, US).
    Each table has rows for crop IDs and columns for pesticides.
    Accepts a list of crop_ids and their corresponding crop_infos."""

    # Ensure crop_ids is a list
    if not isinstance(crop_ids, list):
        crop_ids = [crop_ids]

    # Load the three datasets with CROP_IDs
    try:
        df_il = pd.read_csv('Datasets/IL/IL_With_Crop_IDs.csv')
        df_eu = pd.read_csv('Datasets/EU/EU_With_Crop_IDs.csv')
        df_us = pd.read_csv('Datasets/US/US_With_Crop_IDs.csv')
    except FileNotFoundError as e:
        print(f"Error loading datasets: {e}")
        sys.exit(1)

    # Skip metadata columns
    skip_columns = ['Crop_ID', 'Crop_Map_Name', 'Crop_Data_Name']

    # Create a mapping from crop_id to crop info
    crop_info_map = {crop_ids[i]: crop_infos[i] for i in range(len(crop_ids))}

    def create_table_for_mechanism(df, mechanism_name, crop_ids, crop_info_map):
        """Create a table for a single mechanism with crop IDs as rows"""
        # Filter for the relevant crop IDs
        filtered_df = df[df['Crop_ID'].isin(crop_ids)]

        if filtered_df.empty:
            # Return empty table with just Crop_ID column
            return pd.DataFrame({'Crop_ID': crop_ids})

        # Start with identification columns
        table_data = {
            'Crop_ID': [],
            'English_Name': [],
            'Hebrew_Name': []
        }

        # Get all pesticide columns that have any non-empty values for these crops
        pesticide_columns = []
        for col in df.columns:
            if col in skip_columns:
                continue
            # Check if this pesticide has any non-empty values for our crops
            if filtered_df[col].notna().any() and (filtered_df[col].astype(str).str.strip() != '').any():
                pesticide_columns.append(col)

        # Build the table row by row for each crop ID
        for crop_id in crop_ids:
            crop_data = filtered_df[filtered_df['Crop_ID'] == crop_id]

            # Get crop info for this ID
            crop_info = crop_info_map.get(crop_id, {})
            english_name = crop_info.get('english', '')
            hebrew_name = crop_info.get('hebrew', '')

            if crop_data.empty:
                # Add row with empty values
                table_data['Crop_ID'].append(crop_id)
                table_data['English_Name'].append(english_name)
                table_data['Hebrew_Name'].append(hebrew_name)
                for col in pesticide_columns:
                    if col not in table_data:
                        table_data[col] = []
                    table_data[col].append('')
            else:
                # Combine all rows for this crop_id - take first non-empty value from any row
                table_data['Crop_ID'].append(crop_id)
                table_data['English_Name'].append(english_name)
                table_data['Hebrew_Name'].append(hebrew_name)

                for col in pesticide_columns:
                    if col not in table_data:
                        table_data[col] = []

                    # Find first non-empty value across all rows for this crop_id
                    combined_value = ''
                    for idx in range(len(crop_data)):
                        value = crop_data.iloc[idx][col]
                        if pd.notna(value) and str(value).strip() != '':
                            combined_value = str(value).strip()
                            break

                    table_data[col].append(combined_value)

        return pd.DataFrame(table_data)

    # Create the three tables
    il_table = create_table_for_mechanism(df_il, 'IL', crop_ids, crop_info_map)
    eu_table = create_table_for_mechanism(df_eu, 'EU', crop_ids, crop_info_map)
    us_table = create_table_for_mechanism(df_us, 'US', crop_ids, crop_info_map)

    return il_table, eu_table, us_table


def query_crop_data(hebrew_word):
    """Main function to query crop data from all three datasets and create 3 separate pesticide tables"""

    # Load the mapping
    mapping = load_mapping()

    # Get CROP_ID(s) from Hebrew word
    crop_ids, crop_infos = get_crop_id(mapping, hebrew_word)

    if crop_ids is None:
        print(f"Error: Hebrew word '{hebrew_word}' not found in mapping.")
        return

    print(f"\n{'=' * 80}")
    print(f"Query Results for: {hebrew_word}")
    print(f"{'=' * 80}")

    # Display all matching crops
    if len(crop_ids) == 1:
        crop_info = crop_infos[0]
        print(f"CROP_ID: {crop_ids[0]}")
        print(f"English Name: {crop_info['english']}")
        print(f"Hebrew Name: {crop_info['hebrew']}")
    else:
        print(f"Found {len(crop_ids)} crops with this Hebrew name:")
        for i, (cid, cinfo) in enumerate(zip(crop_ids, crop_infos), 1):
            print(f"  {i}. CROP_ID: {cid}")
            print(f"     English Name: {cinfo['english']}")
            print(f"     Hebrew Name: {cinfo['hebrew']}")
            if 'translation_source' in cinfo:
                print(f"     Source: {cinfo['translation_source']}")

    print(f"{'=' * 80}\n")

    # Create 3 separate pesticide tables for these crops
    print("Creating pesticide tables by mechanism...")
    il_table, eu_table, us_table = create_pesticide_tables_by_mechanism(crop_ids, crop_infos)

    # Filter out empty tables (no pesticide restrictions)
    # A table is considered empty if it only has the identification columns (Crop_ID, English_Name, Hebrew_Name)
    tables_to_display = []
    saved_files = []
    base_filename = hebrew_word.replace(" ", "_")

    # Check IL Table
    num_il_pesticides = len(il_table.columns) - 3  # -3 for identification columns
    if num_il_pesticides > 0:
        tables_to_display.append(('IL', il_table, num_il_pesticides))
        il_file = f'pesticide_IL_{base_filename}.csv'
        il_table.to_csv(il_file, index=False)
        saved_files.append(('IL', il_file))

    # Check EU Table
    num_eu_pesticides = len(eu_table.columns) - 3
    if num_eu_pesticides > 0:
        tables_to_display.append(('EU', eu_table, num_eu_pesticides))
        eu_file = f'pesticide_EU_{base_filename}.csv'
        eu_table.to_csv(eu_file, index=False)
        saved_files.append(('EU', eu_file))

    # Check US Table
    num_us_pesticides = len(us_table.columns) - 3
    if num_us_pesticides > 0:
        tables_to_display.append(('US', us_table, num_us_pesticides))
        us_file = f'pesticide_US_{base_filename}.csv'
        us_table.to_csv(us_file, index=False)
        saved_files.append(('US', us_file))

    # Display only non-empty tables
    if not tables_to_display:
        print("\nNo pesticide restrictions found for any mechanism (IL, EU, US).")
        print("This crop has no MRL limitations.")
    else:
        for mechanism, table, num_pesticides in tables_to_display:
            print(f"\n{'=' * 80}")
            print(f"{mechanism} Mechanism - Pesticide Data:")
            print(f"{'=' * 80}")
            print(f"Found {num_pesticides} pesticides for {len(table)} crop ID(s)")
            print(table.to_string(index=False))
            print()

        # Display saved files
        print(f"{'=' * 80}")
        print(f"Tables saved to:")
        for mechanism, filepath in saved_files:
            print(f"  - {mechanism}: {filepath}")
        print(f"{'=' * 80}")

    return il_table, eu_table, us_table


if __name__ == "__main__":
    # Define the Hebrew word to search for
    he_word = "תפוח עץ"

    query_crop_data(he_word)
