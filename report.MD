
שלבים בהכנת הדאטה:

1. run 'reorganize_data'.py':

Processing IL dataset... 
    Resolving duplicates for IL...
      Found 2 duplicate rows
      ✓ Resolved to 3698 unique rows
    ✓ IL dataset reorganized: 136 crops × 268 active ingredients

Processing EU dataset...
    Resolving duplicates for EU...
      Found 459580 duplicate rows
      ✓ Resolved to 208012 unique rows
      ⚠️  1217 conflicts with same date but different MRL values
      ✓ Saved to: Datasets/EU_Same_Date_Conflicts.csv
      ✓ These values are kept as comma-separated lists in the reorganized file
    
      First few conflicts:
        Crop: (a) edible peel
        Pesticide: Bromide ion
        Date: 2008-09-01 00:00:00
        MRL values: [np.float64(10.0), np.float64(20.0)]
        ------------------------------------------------------------
        Crop: (a) grapes
        Pesticide: Bromide ion
        Date: 2008-09-01 00:00:00
        MRL values: [np.float64(5.0), np.float64(20.0)]
        ------------------------------------------------------------
        Crop: (b) leaves and herbs
        Pesticide: Bromide ion
        Date: 2008-09-01 00:00:00
        MRL values: [np.float64(50.0), np.float64(100.0)]
        ------------------------------------------------------------
        Crop: (b) strawberries
        Pesticide: Bromide ion
        Date: 2008-09-01 00:00:00
        MRL values: [np.float64(20.0), np.float64(30.0)]
        ------------------------------------------------------------
        Crop: (c) cane fruits
        Pesticide: Bromide ion
        Date: 2008-09-01 00:00:00
        MRL values: [np.float64(5.0), np.float64(20.0)]
        ------------------------------------------------------------
✓ EU dataset reorganized: 302 crops × 526 pesticides

✓ US dataset is already organized correctly

==================================================
Summary:
==================================================
IL: Datasets/IL/IL_Reorganized.csv
EU: Datasets/EU/EU_Reorganized.csv
US: Datasets/US/US_full_pesticide_matrix.csv (unchanged)

Duplicate Resolution Strategy:
  1. For each Crop+Pesticide combination, keep the entry with the most recent date
  2. If multiple entries exist on the same date with different MRL values,
     keep ALL values as a comma-separated list in the cell
  3. Conflicts are also saved to separate CSV files for review

Process finished with exit code 0



--------------------------------------------------------

2. run 'build_id_he_en.py':

  ✓ Enhanced mapping created successfully!
  ✓ Active Ingredients (Pesticides): 1008 items
  ✓ Crops: 1154 items
  - Crops with Hebrew translation: 136
  - Crops without Hebrew translation: 1018
  - Crops without Hebrew (before fuzzy matching): 2443
  - 
  Datasets included: IL (golden), EU, US

  Enhancements:
    - Pesticides: Added unique pesticides from EU and US datasets
    - Crops: Applied fuzzy matching (remove/add 's', substring matching)

--------------------------------------------------------

3. run 'add_crops_ids.py':

✓ Crop IDs added successfully to all datasets!
✓ IL dataset: 136 rows
  - Rows with Crop_ID: 136
  - Rows without Crop_ID: 0
  - Rows with Hebrew name in mapping: 136
✓ EU dataset: 302 rows
  - Rows with Crop_ID: 302
  - Rows without Crop_ID: 0
  - Rows with Hebrew name in mapping: 135
✓ US dataset: 2151 rows
  - Rows with Crop_ID: 2151
  - Rows without Crop_ID: 0
  - Rows with Hebrew name in mapping: 784

New files created:
  - Datasets/IL/IL_With_Crop_IDs.csv
  - Datasets/EU/EU_With_Crop_IDs.csv
  - Datasets/US/US_With_Crop_IDs.csv


--------------------------------------------------------

4. תחילת תהליך תרגום ה crops חסרי התרגום
הרץ את הסקריפט למציאת גידולים ללא תרגום:

    - python translate_missing_crops.py

    הסקריפט:
    - יקרא את [golden_mapping.json](golden_mapping.json)
      - ימצא את כל הגידולים ללא תרגום עברי
      - ישלח אותם בחבילות ל-Azure OpenAI LLM
      - ישמור את ההצעות ב-[translation_suggestions.json](translation_suggestions.json)

    ✓ Processed 1010 crop translations
    
    📊 Summary:
       - Using existing Hebrew translations: 206
         - New translations suggested: 804
    
    💾 Saving suggestions to translation_suggestions.json...
    ✓ Saved to translation_suggestions.json

--------------------------------------------------------

5. השתמש בתרגומים המוצעים כדי למלא את המיפוי

python apply_translations.py

הסקריפט:
- יקרא את [golden_mapping.json](golden_mapping.json) (לקריאה בלבד - לא משנה אותו!)
- יקרא את [translation_suggestions.json](translation_suggestions.json)
- ייצור עותק עמוק של הנתונים
- יוסיף שדה `translation_source` לכל הגידולים
- יוסיף את התרגומים החדשים
- ישמור הכל ב-[golden_mapping_expanded.json](golden_mapping_expanded.json) חדש

**פלט:**

```
================================================================================
APPLY TRANSLATIONS - Create golden_mapping_expanded.json
================================================================================

📂 Loading translation_suggestions.json...
   ✓ Loaded 1010 suggestions

📂 Loading golden_mapping.json (read-only)...
   ✓ Loaded golden mapping

📋 Creating expanded mapping...
   ✓ Created copy

🏷️  Adding translation_source field to existing crops...
   ✓ Marked all original Hebrew translations as 'golden'

🔄 Applying LLM-generated translations...

📊 SUMMARY:
   - Total suggestions processed: 1010
   - Translations applied: 1010
   - Used existing Hebrew: 206
   - New translations: 804
   - Skipped (already has Hebrew): 0
   - Errors: 0

💾 Saving expanded mapping to golden_mapping_expanded.json...
   ✓ Saved successfully

📊 Statistics:
   - Total crops: 1154
   - Crops with Hebrew: 1146
   - Crops without Hebrew: 8
   - Golden translations (original): 136
   - LLM-generated translations: 1010

================================================================================
✅ DONE!
Created: golden_mapping_expanded.json
golden_mapping.json was NOT modified (remains as original)
================================================================================

--------------------------------------------------------

6. הפעל את האפליקצייה

