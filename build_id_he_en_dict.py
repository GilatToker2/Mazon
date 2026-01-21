import pandas as pd
import json
import re

# Read the three main reorganized datasets
df_il = pd.read_csv('Datasets/IL/IL_Reorganized.csv')
df_eu = pd.read_csv('Datasets/EU/EU_Reorganized.csv')
df_us = pd.read_csv('Datasets/US/US_full_pesticide_matrix.csv')

# Read the Hebrew-English mapping datasets for crops
df_en = pd.read_csv('Datasets/IL/IL_En.csv')
df_he = pd.read_csv('Datasets/IL/IL_He.csv')

# Create Hebrew mappings for crops only (from IL dataset - this is the golden source)
hebrew_crop_map = {}

# Build Hebrew mappings from IL_En and IL_He
for idx in range(len(df_en)):
    crop_en = df_en.iloc[idx]['Crop']
    crop_he = df_he.iloc[idx]['גידול']

    if crop_en not in hebrew_crop_map:
        hebrew_crop_map[crop_en] = crop_he

# Collect all unique pesticides from IL dataset first (golden source)
all_pesticides = {}

# From IL dataset (columns are pesticides, except 'Crop')
for col in df_il.columns:
    if col != 'Crop':
        all_pesticides[col.upper()] = col  # Store normalized -> original

# Add pesticides from EU dataset if they don't exist
for col in df_eu.columns:
    if col != 'Crop':
        normalized = col.upper()
        if normalized not in all_pesticides:
            all_pesticides[normalized] = col

# Add pesticides from US dataset if they don't exist
for col in df_us.columns:
    if col != 'Commodity':
        normalized = col.upper()
        if normalized not in all_pesticides:
            all_pesticides[normalized] = col

# Create ID mapping for all pesticides (no Hebrew names)
active_ingredients = {}
pesticide_id = 1

for normalized_name in sorted(all_pesticides.keys()):
    original_name = all_pesticides[normalized_name]
    active_ingredients[pesticide_id] = {
        'id': pesticide_id,
        'name': original_name
    }

    # Also store by name for quick lookup
    active_ingredients[original_name] = pesticide_id
    pesticide_id += 1


# Helper function for fuzzy crop matching
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


# Collect all unique crops from IL dataset first (golden source with Hebrew names)
all_crops = {}

# Track crops and their matching status (for statistics)
crops_with_exact_match = set()  # Crops that matched exactly to IL
crops_with_fuzzy_match = {}  # Crops that matched via fuzzy -> what they matched to
crops_without_match = set()  # Crops that didn't match at all

# From IL dataset
for crop in df_il['Crop'].unique():
    all_crops[crop.upper()] = crop
    crops_with_exact_match.add(crop)

# Add crops from EU dataset with fuzzy matching
for crop in df_eu['Crop'].unique():
    matched = fuzzy_match_crop(crop, all_crops.values())
    if matched:
        # Use the existing crop name (from IL)
        crops_with_fuzzy_match[crop] = matched
        continue
    else:
        # Add as new crop
        all_crops[crop.upper()] = crop
        crops_without_match.add(crop)

# Add crops from US dataset with fuzzy matching
for crop in df_us['Commodity'].unique():
    matched = fuzzy_match_crop(crop, all_crops.values())
    if matched:
        # Use the existing crop name
        crops_with_fuzzy_match[crop] = matched
        continue
    else:
        # Add as new crop
        all_crops[crop.upper()] = crop
        crops_without_match.add(crop)

# Calculate statistics
# Crops without Hebrew if we didn't use fuzzy matching
crops_without_hebrew_no_fuzzy = 0
for crop in crops_with_exact_match:
    if crop not in hebrew_crop_map or not hebrew_crop_map.get(crop):
        crops_without_hebrew_no_fuzzy += 1

# Add crops that matched via fuzzy (they would be separate without fuzzy)
for crop in crops_with_fuzzy_match:
    crops_without_hebrew_no_fuzzy += 1

# Add crops that didn't match at all
for crop in crops_without_match:
    if crop not in hebrew_crop_map or not hebrew_crop_map.get(crop):
        crops_without_hebrew_no_fuzzy += 1

# Create ID mapping for all crops (with Hebrew names where available)
crops = {}
crop_id = 1

# Statistics counters
crops_with_hebrew = 0
crops_without_hebrew = 0

for normalized_name in sorted(all_crops.keys()):
    original_name = all_crops[normalized_name]
    hebrew_name = hebrew_crop_map.get(original_name, '')

    crops[crop_id] = {
        'id': crop_id,
        'english': original_name,
        'hebrew': hebrew_name,
    }

    # Count statistics
    if hebrew_name:
        crops_with_hebrew += 1
    else:
        crops_without_hebrew += 1

    # Store by English name for quick lookup
    crops[original_name] = crop_id

    # Also store by Hebrew name for quick lookup (if exists)
    if hebrew_name:
        crops[hebrew_name] = crop_id

    crop_id += 1

# Create the final mapping structure
mapping = {
    'active_ingredients': active_ingredients,
    'crops': crops,
    'metadata': {
        'total_pesticides': pesticide_id - 1,
        'total_crops': crop_id - 1,
        'datasets': ['IL', 'EU', 'US']
    }
}

# Save to JSON file
with open('golden_mapping.json', 'w', encoding='utf-8') as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)

print("✓ Enhanced mapping created successfully!")
print(f"✓ Active Ingredients (Pesticides): {pesticide_id - 1} items")
print(f"✓ Crops: {crop_id - 1} items")
print(f"  - Crops with Hebrew translation: {crops_with_hebrew}")
print(f"  - Crops without Hebrew translation: {crops_without_hebrew}")
print(f"  - Crops without Hebrew (before fuzzy matching): {crops_without_hebrew_no_fuzzy}")
print(f"\nDatasets included: IL (golden), EU, US")
print("\nEnhancements:")
print("  - Pesticides: Added unique pesticides from EU and US datasets")
print("  - Crops: Applied fuzzy matching (remove/add 's', substring matching)")
print("\nUsage examples:")
print("  # Load the mapping")
print("  data = json.load(open('golden_mapping.json', encoding='utf-8'))")
print()
print("  # Search pesticide by name to get ID:")
print("  pesticide_id = data['active_ingredients']['ABAMECTIN']")
print("  print(pesticide_id)  # Returns the ID")
print()
print("  # Search crop by English name to get ID:")
print("  crop_id = data['crops']['APPLE']")
print("  print(crop_id)  # Returns the ID")
print()
print("  # Search crop by Hebrew name to get ID:")
print("  crop_id = data['crops']['תפוח עץ']")
print("  print(crop_id)  # Returns the ID")
print()
print("  # Search by ID to get full info:")
print("  pesticide_info = data['active_ingredients'][str(pesticide_id)]")
print("  print(pesticide_info)  # Returns {'id': X, 'name': 'ABAMECTIN'}")
print()
print("  crop_info = data['crops'][str(crop_id)]")
print("  print(crop_info)  # Returns {'id': X, 'english': 'APPLE', 'hebrew': 'תפוח עץ'}")
