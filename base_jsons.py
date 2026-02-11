"""
Create base JSON files from Israeli dataset
--------------------------------------------
This script loads both Hebrew and English Israeli datasets and creates:
1. crops.json - List of all unique crops with ID, Hebrew name, and English name
2. pesticides.json - List of all unique pesticides with ID and name (English only)

The script maps Hebrew to English names row-by-row for crops.
Pesticides use English names only as they originate in English.
"""

import pandas as pd
import json
from pathlib import Path


def load_israeli_datasets(csv_path_he, csv_path_en):
    """Load both Hebrew and English Israeli datasets"""
    print(f"Loading Hebrew dataset: {csv_path_he}")
    df_he = pd.read_csv(csv_path_he, encoding='utf-8-sig')
    print(f"Loaded {len(df_he)} rows")

    print(f"Loading English dataset: {csv_path_en}")
    df_en = pd.read_csv(csv_path_en, encoding='utf-8-sig')
    print(f"Loaded {len(df_en)} rows")

    # Verify both datasets have same number of rows
    if len(df_he) != len(df_en):
        print(f"WARNING: Row count mismatch - Hebrew: {len(df_he)}, English: {len(df_en)}")

    return df_he, df_en


def create_crops_json(df_he, df_en, output_path):
    """Create JSON file with all unique crops and IDs (Hebrew and English)"""
    print("\nCreating crops JSON...")

    # Create mapping of Hebrew to English crop names from the datasets
    crop_mapping = {}
    for idx in range(len(df_he)):
        crop_he = df_he.iloc[idx]['גידול']
        crop_en = df_en.iloc[idx]['Crop']
        if pd.notna(crop_he) and pd.notna(crop_en):
            crop_mapping[crop_he] = crop_en

    # Extract unique crops
    unique_crops = sorted(crop_mapping.keys())  # Alphabetical sort

    # Create list with IDs
    crops_list = []
    for idx, crop_he in enumerate(unique_crops, start=1):
        crops_list.append({
            "id": idx,
            "name_he": crop_he,
            "name_en": crop_mapping[crop_he]
        })

    # Save to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(crops_list, f, ensure_ascii=False, indent=2)

    print(f"Created file: {output_path}")
    print(f"Total {len(crops_list)} unique crops")

    return crops_list


def create_pesticides_json(df_en, output_path):
    """Create JSON file with all unique pesticides and IDs"""
    print("\nCreating pesticides JSON...")

    # Extract unique pesticides from English dataset
    unique_pesticides = df_en['Active Ingredient'].dropna().unique()
    unique_pesticides = sorted(unique_pesticides)  # Alphabetical sort

    # Create list with IDs
    pesticides_list = []
    for idx, pesticide_name in enumerate(unique_pesticides, start=1):
        pesticides_list.append({
            "id": idx,
            "name": pesticide_name
        })

    # Save to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(pesticides_list, f, ensure_ascii=False, indent=2)

    print(f"Created file: {output_path}")
    print(f"Total {len(pesticides_list)} unique pesticides")

    return pesticides_list


def main():
    print("=" * 70)
    print("Creating base JSON files from Israeli dataset")
    print("=" * 70)

    # Paths
    dataset_path_he = Path("Datasets/IL/IL_He.csv")
    dataset_path_en = Path("Datasets/IL/IL_En.csv")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    crops_output = output_dir / "crops.json"
    pesticides_output = output_dir / "pesticides.json"

    # Load both datasets
    df_he, df_en = load_israeli_datasets(dataset_path_he, dataset_path_en)

    # Create JSON files
    crops = create_crops_json(df_he, df_en, crops_output)
    pesticides = create_pesticides_json(df_en, pesticides_output)

    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70)
    print(f"Files created:")
    print(f"   - {crops_output} ({len(crops)} crops)")
    print(f"   - {pesticides_output} ({len(pesticides)} pesticides)")
    print("=" * 70)


if __name__ == "__main__":
    main()
