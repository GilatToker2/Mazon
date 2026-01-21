import pandas as pd
import json

# Load the golden mapping
with open('golden_mapping.json', 'r', encoding='utf-8') as f:
    mapping = json.load(f)

# Read the three reorganized datasets
df_il = pd.read_csv('Datasets/IL/IL_Reorganized.csv')
df_eu = pd.read_csv('Datasets/EU/EU_Reorganized.csv')
df_us = pd.read_csv('Datasets/US/US_full_pesticide_matrix.csv')


# Helper function for fuzzy crop matching (same as in build_id_he_en_dict.py)
def fuzzy_match_crop(crop_name, existing_crops):
    """
    Try to match a crop name to existing crops using various manipulations:
    - Convert to lowercase for comparison
    - Remove trailing 's'
    - Check if the crop word appears in existing crops (e.g., "banana" matches "The bananas")
    """
    crop_lower = crop_name.lower().strip()

    # First, try exact match (case-insensitive)
    for existing in existing_crops:
        if existing.lower().strip() == crop_lower:
            return existing

    # Try removing trailing 's' from the new crop
    if crop_lower.endswith('s'):
        crop_without_s = crop_lower[:-1]
        for existing in existing_crops:
            existing_lower = existing.lower().strip()
            if existing_lower == crop_without_s or existing_lower == crop_without_s + 's':
                return existing

    # Try adding 's' to the new crop
    crop_with_s = crop_lower + 's'
    for existing in existing_crops:
        existing_lower = existing.lower().strip()
        if existing_lower == crop_with_s:
            return existing

    # Check if the crop word appears in existing crops (word-level matching)
    # This handles cases like "banana" matching "The bananas"
    for existing in existing_crops:
        existing_lower = existing.lower().strip()

        # Check if one contains the other as substring (for multi-word matches)
        if crop_lower in existing_lower or existing_lower in crop_lower:
            # Make sure it's a meaningful match (not just a substring)
            if len(crop_lower) > 3 and len(existing_lower) > 3:
                return existing

    return None


# Get all crop names from the mapping (for fuzzy matching)
all_crop_names = []
for key, value in mapping['crops'].items():
    if isinstance(value, dict) and 'english' in value:
        all_crop_names.append(value['english'])


# Function to get crop ID and matched name from mapping with fuzzy matching
def get_crop_info(crop_name):
    """Get the crop ID and matched name from the mapping, using fuzzy matching if exact match fails"""
    # Try exact match first
    if crop_name in mapping['crops']:
        return mapping['crops'][crop_name], crop_name

    # Try fuzzy matching
    matched_crop = fuzzy_match_crop(crop_name, all_crop_names)
    if matched_crop and matched_crop in mapping['crops']:
        return mapping['crops'][matched_crop], matched_crop

    return None, None


# Process IL dataset
il_crop_info = df_il['Crop'].apply(get_crop_info)
df_il.insert(0, 'Crop_ID', [info[0] for info in il_crop_info])
df_il.insert(1, 'Crop_Map_Name', [info[1] for info in il_crop_info])
df_il.rename(columns={'Crop': 'Crop_Data_Name'}, inplace=True)

# Process EU dataset
eu_crop_info = df_eu['Crop'].apply(get_crop_info)
df_eu.insert(0, 'Crop_ID', [info[0] for info in eu_crop_info])
df_eu.insert(1, 'Crop_Map_Name', [info[1] for info in eu_crop_info])
df_eu.rename(columns={'Crop': 'Crop_Data_Name'}, inplace=True)

# Process US dataset (note: US uses 'Commodity' instead of 'Crop')
us_crop_info = df_us['Commodity'].apply(get_crop_info)
df_us.insert(0, 'Crop_ID', [info[0] for info in us_crop_info])
df_us.insert(1, 'Crop_Map_Name', [info[1] for info in us_crop_info])
df_us.rename(columns={'Commodity': 'Crop_Data_Name'}, inplace=True)

# Save the updated datasets with new names (as copies)
df_il.to_csv('Datasets/IL/IL_With_Crop_IDs.csv', index=False)
df_eu.to_csv('Datasets/EU/EU_With_Crop_IDs.csv', index=False)
df_us.to_csv('Datasets/US/US_With_Crop_IDs.csv', index=False)


# Count crops with Hebrew names in each dataset
def count_hebrew(df):
    """Count rows where the crop has Hebrew name in mapping"""
    hebrew_count = 0

    for crop_id in df['Crop_ID'].dropna().unique():
        crop_id_str = str(int(crop_id))
        if crop_id_str in mapping['crops']:
            crop_info = mapping['crops'][crop_id_str]
            if isinstance(crop_info, dict):
                # Check if has Hebrew name
                if 'hebrew' in crop_info and crop_info['hebrew']:
                    hebrew_count += (df['Crop_ID'] == crop_id).sum()

    return hebrew_count


il_hebrew = count_hebrew(df_il)
eu_hebrew = count_hebrew(df_eu)
us_hebrew = count_hebrew(df_us)

print("✓ Crop IDs added successfully to all datasets!")
print(f"✓ IL dataset: {len(df_il)} rows")
print(f"  - Rows with Crop_ID: {df_il['Crop_ID'].notna().sum()}")
print(f"  - Rows without Crop_ID: {df_il['Crop_ID'].isna().sum()}")
print(f"  - Rows with Hebrew name in mapping: {il_hebrew}")
print(f"✓ EU dataset: {len(df_eu)} rows")
print(f"  - Rows with Crop_ID: {df_eu['Crop_ID'].notna().sum()}")
print(f"  - Rows without Crop_ID: {df_eu['Crop_ID'].isna().sum()}")
print(f"  - Rows with Hebrew name in mapping: {eu_hebrew}")
print(f"✓ US dataset: {len(df_us)} rows")
print(f"  - Rows with Crop_ID: {df_us['Crop_ID'].notna().sum()}")
print(f"  - Rows without Crop_ID: {df_us['Crop_ID'].isna().sum()}")
print(f"  - Rows with Hebrew name in mapping: {us_hebrew}")
print("\nNew files created:")
print("  - Datasets/IL/IL_With_Crop_IDs.csv")
print("  - Datasets/EU/EU_With_Crop_IDs.csv")
print("  - Datasets/US/US_With_Crop_IDs.csv")
