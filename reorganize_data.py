import pandas as pd

# ============================================
# Resolve duplicates by date
# ============================================
def resolve_duplicates_by_date(df, dataset_name, crop_col, pesticide_col, mrl_col, date_col):
    """
    Resolve duplicates by keeping the most recent entry.
    If multiple entries exist on the same date with different MRL values, keep them as a list.
    """
    print(f"\nResolving duplicates for {dataset_name}...")

    # Convert date column to datetime
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    # Find duplicates
    duplicates_mask = df.duplicated(subset=[crop_col, pesticide_col], keep=False)
    duplicates = df[duplicates_mask].copy()

    if len(duplicates) == 0:
        print(f"✓ {dataset_name}: No duplicates found")
        return df, pd.DataFrame()

    print(f"  Found {len(duplicates)} duplicate rows")

    # Group by crop and pesticide
    grouped = duplicates.groupby([crop_col, pesticide_col])

    resolved_rows = []
    same_date_conflicts = []

    for (crop, pesticide), group in grouped:
        # Sort by date (most recent first)
        group_sorted = group.sort_values(date_col, ascending=False)

        # Get the most recent date
        max_date = group_sorted[date_col].max()

        # Get all rows with the most recent date
        most_recent = group_sorted[group_sorted[date_col] == max_date]

        # Check if there are different MRL values on the same date
        unique_mrls = most_recent[mrl_col].dropna().unique()

        if len(most_recent) == 0:
            # Skip if no valid rows
            continue

        if len(unique_mrls) > 1:
            # Conflict: same date, different MRL values - keep as list
            mrl_list = ', '.join(map(str, unique_mrls))
            same_date_conflicts.append({
                crop_col: crop,
                pesticide_col: pesticide,
                date_col: max_date,
                'MRL_values': list(unique_mrls),
                'count': len(most_recent)
            })
            # Create a row with the list of values
            row = most_recent.iloc[0].copy()
            row[mrl_col] = mrl_list
            resolved_rows.append(row)
        else:
            # No conflict, just take the most recent
            resolved_rows.append(most_recent.iloc[0])

    # Create cleaned dataframe
    non_duplicates = df[~duplicates_mask]
    resolved_df = pd.concat([non_duplicates, pd.DataFrame(resolved_rows)], ignore_index=True)

    print(f"  ✓ Resolved to {len(resolved_df)} unique rows")

    # Save conflicts if any
    if len(same_date_conflicts) > 0:
        conflicts_df = pd.DataFrame(same_date_conflicts)
        conflicts_df.to_csv(f'Datasets/{dataset_name}/{dataset_name}_Same_Date_Conflicts.csv', index=False, encoding='utf-8-sig')
        print(f"  ⚠️  {len(same_date_conflicts)} conflicts with same date but different MRL values")
        print(f"  ✓ Saved to: Datasets/{dataset_name}/{dataset_name}_Same_Date_Conflicts.csv")
        print(f"  ✓ These values are kept as comma-separated lists in the reorganized file")

        # Show first few conflicts
        print("\n  First few conflicts:")
        for conflict in same_date_conflicts[:5]:
            print(f"    {crop_col}: {conflict[crop_col]}")
            print(f"    {pesticide_col}: {conflict[pesticide_col]}")
            print(f"    Date: {conflict[date_col]}")
            print(f"    MRL values: {conflict['MRL_values']}")
            print("    " + "-" * 60)

    return resolved_df, pd.DataFrame(same_date_conflicts)


# ============================================
# Reorganize IL Dataset
# ============================================
print("Processing IL dataset...")
df_il = pd.read_csv('Datasets/IL/IL_En.csv')

# Resolve duplicates by date
df_il_clean, il_conflicts = resolve_duplicates_by_date(
    df_il, 'IL', 'Crop', 'Active Ingredient', 'MRL', 'Update Date'
)

# Pivot: Rows = Crop, Columns = Active Ingredient, Values = MRL
il_pivot = df_il_clean.pivot_table(
    index='Crop',
    columns='Active Ingredient',
    values='MRL',
    aggfunc='first'  # Safe to use 'first' since duplicates are resolved
)

# Save reorganized IL data
il_pivot.to_csv('Datasets/IL/IL_Reorganized.csv', encoding='utf-8-sig')
print(f"✓ IL dataset reorganized: {il_pivot.shape[0]} crops × {il_pivot.shape[1]} active ingredients")

# ============================================
# Reorganize EU Dataset
# ============================================
print("\nProcessing EU dataset...")
df_eu = pd.read_csv('Datasets/EU/EU_MRL_Final_Database.csv')

# Resolve duplicates by date
df_eu_clean, eu_conflicts = resolve_duplicates_by_date(
    df_eu, 'EU', 'Crop', 'Pesticide', 'MRL_Limit_mg_kg', 'Valid_From'
)

# Pivot: Rows = Crop, Columns = Pesticide, Values = MRL_Limit_mg_kg
eu_pivot = df_eu_clean.pivot_table(
    index='Crop',
    columns='Pesticide',
    values='MRL_Limit_mg_kg',
    aggfunc='first'  # Safe to use 'first' since duplicates are resolved
)

# Save reorganized EU data
eu_pivot.to_csv('Datasets/EU/EU_Reorganized.csv', encoding='utf-8-sig')
print(f"✓ EU dataset reorganized: {eu_pivot.shape[0]} crops × {eu_pivot.shape[1]} pesticides")

# ============================================
# US Dataset (already organized)
# ============================================
print("\n✓ US dataset is already organized correctly")

print("\n" + "=" * 50)
print("Summary:")
print("=" * 50)
print(f"IL: Datasets/IL/IL_Reorganized.csv")
print(f"EU: Datasets/EU/EU_Reorganized.csv")
print(f"US: Datasets/US/US_full_pesticide_matrix.csv (unchanged)")
print("\nDuplicate Resolution Strategy:")
print("  1. For each Crop+Pesticide combination, keep the entry with the most recent date")
print("  2. If multiple entries exist on the same date with different MRL values,")
print("     keep ALL values as a comma-separated list in the cell")
print("  3. Conflicts are also saved to separate CSV files for review")
