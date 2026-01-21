"""
Script to apply approved translations from translation_suggestions.json.

IMPORTANT:
- This script DOES NOT modify golden_mapping.json
- It creates a NEW file: golden_mapping_expanded.json
- Each crop keeps its original ID
- Adds 'translation_source' field: 'golden' or 'llm_generated'

After reviewing and approving the suggestions in translation_suggestions.json,
run this script to create the expanded mapping file.
"""

import json
from datetime import datetime
from copy import deepcopy


def apply_translations():
    """Apply approved translations to create golden_mapping_expanded.json."""

    print("=" * 80)
    print("APPLY TRANSLATIONS - Create golden_mapping_expanded.json")
    print("=" * 80)
    print()

    # Load translation suggestions
    print("📂 Loading translation_suggestions.json...")
    try:
        with open('translation_suggestions.json', 'r', encoding='utf-8') as f:
            suggestions_data = json.load(f)
    except FileNotFoundError:
        print("❌ Error: translation_suggestions.json not found!")
        print("   Please run translate_missing_crops.py first.")
        return

    suggestions = suggestions_data.get('suggestions', [])
    print(f"   ✓ Loaded {len(suggestions)} suggestions")
    print()

    # Load golden mapping (READ ONLY - we will NOT modify this)
    print("📂 Loading golden_mapping.json (read-only)...")
    with open('golden_mapping.json', 'r', encoding='utf-8') as f:
        original_mapping = json.load(f)
    print("   ✓ Loaded golden mapping")
    print()

    # Create a deep copy for the expanded mapping
    print("📋 Creating expanded mapping...")
    expanded_mapping = deepcopy(original_mapping)
    crops = expanded_mapping['crops']
    print("   ✓ Created copy")
    print()

    # First pass: Add translation_source to all existing crops with Hebrew
    print("🏷️  Adding translation_source field to existing crops...")
    for key, value in crops.items():
        # Only process numeric keys (actual crop entries)
        if isinstance(key, str) and key.isdigit():
            if value.get('hebrew'):
                # This crop already has Hebrew from the golden source
                value['translation_source'] = 'golden'

    print("   ✓ Marked all original Hebrew translations as 'golden'")
    print()

    # Apply new translations
    print("🔄 Applying LLM-generated translations...")
    print()

    applied_count = 0
    use_existing_count = 0
    new_translation_count = 0
    skipped_count = 0
    errors = []

    for suggestion in suggestions:
        action = suggestion.get('action')
        crop_id = suggestion.get('id')
        english_name = suggestion.get('english')
        suggested_hebrew = suggestion.get('suggested_hebrew')

        crop_id_str = str(crop_id)

        # Validate that crop exists
        if crop_id_str not in crops:
            errors.append(f"Crop ID {crop_id} not found in golden_mapping")
            continue

        crop_data = crops[crop_id_str]

        # Check if crop already has Hebrew translation
        if crop_data.get('hebrew'):
            skipped_count += 1
            print(f"   ⏭ Skipped ID {crop_id} ({english_name}) - already has Hebrew: {crop_data['hebrew']}")
            continue

        # Validate suggested_hebrew exists
        if not suggested_hebrew:
            errors.append(f"Missing suggested_hebrew for crop ID {crop_id}")
            continue

        # Add the Hebrew translation (keeping the original ID)
        crop_data['hebrew'] = suggested_hebrew
        crop_data['translation_source'] = 'llm_generated'

        # Add Hebrew lookup to enable searching by Hebrew name
        # Support multiple IDs per Hebrew name (in case of duplicates)
        if suggested_hebrew in crops:
            # Hebrew name already exists
            existing_value = crops[suggested_hebrew]
            if isinstance(existing_value, list):
                # Already a list, append if not duplicate
                if crop_id not in existing_value:
                    existing_value.append(crop_id)
            else:
                # Convert to list with both IDs
                if existing_value != crop_id:
                    crops[suggested_hebrew] = [existing_value, crop_id]
        else:
            # First time seeing this Hebrew name
            crops[suggested_hebrew] = crop_id

        applied_count += 1

        if action == 'use_existing_hebrew':
            use_existing_count += 1
            source_crop_id = suggestion.get('source_crop_id', 'N/A')
            print(f"   ✓ ID {crop_id} ({english_name}) -> {suggested_hebrew} (from crop ID {source_crop_id})")
        elif action == 'new_translation':
            new_translation_count += 1
            print(f"   ✓ ID {crop_id} ({english_name}) -> {suggested_hebrew} (new translation)")
        else:
            print(f"   ✓ ID {crop_id} ({english_name}) -> {suggested_hebrew}")

    print()
    print("=" * 80)
    print("📊 SUMMARY:")
    print(f"   - Total suggestions processed: {len(suggestions)}")
    print(f"   - Translations applied: {applied_count}")
    print(f"   - Used existing Hebrew: {use_existing_count}")
    print(f"   - New translations: {new_translation_count}")
    print(f"   - Skipped (already has Hebrew): {skipped_count}")
    print(f"   - Errors: {len(errors)}")
    print()

    if errors:
        print("⚠ ERRORS:")
        for error in errors:
            print(f"   - {error}")
        print()

    # Calculate statistics
    crops_with_hebrew = 0
    crops_without_hebrew = 0
    golden_translations = 0
    llm_translations = 0

    for key, value in crops.items():
        if isinstance(key, str) and key.isdigit():
            if value.get('hebrew'):
                crops_with_hebrew += 1
                if value.get('translation_source') == 'golden':
                    golden_translations += 1
                elif value.get('translation_source') == 'llm_generated':
                    llm_translations += 1
            else:
                crops_without_hebrew += 1

    # Update metadata
    expanded_mapping['metadata']['translation_info'] = {
        'golden_translations': golden_translations,
        'llm_generated_translations': llm_translations,
        'total_with_hebrew': crops_with_hebrew,
        'total_without_hebrew': crops_without_hebrew,
        'last_updated': datetime.now().isoformat()
    }

    # Save expanded mapping
    output_file = 'golden_mapping_expanded.json'
    print(f"💾 Saving expanded mapping to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(expanded_mapping, f, ensure_ascii=False, indent=2)
    print(f"   ✓ Saved successfully")
    print()

    print("📊 Statistics:")
    print(f"   - Total crops: {crops_with_hebrew + crops_without_hebrew}")
    print(f"   - Crops with Hebrew: {crops_with_hebrew}")
    print(f"   - Crops without Hebrew: {crops_without_hebrew}")
    print(f"   - Golden translations (original): {golden_translations}")
    print(f"   - LLM-generated translations: {llm_translations}")
    print()

    print("=" * 80)
    print("✅ DONE!")
    print(f"Created: {output_file}")
    print("golden_mapping.json was NOT modified (remains as original)")
    print("=" * 80)


if __name__ == "__main__":
    apply_translations()
