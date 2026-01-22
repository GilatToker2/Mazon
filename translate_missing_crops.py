"""
Script to translate missing Hebrew crop names using Azure OpenAI LLM.

This script:
1. Reads golden_mapping.json (DOES NOT MODIFY IT)
2. Finds all crops without Hebrew translation
3. Sends them in chunks to Azure OpenAI LLM
4. LLM suggests Hebrew translation for each crop (uses existing or suggests new)
5. Saves suggestions to translation_suggestions.json for manual review

IMPORTANT:
- golden_mapping.json is NEVER modified
- Each crop keeps its original ID
- New field 'translation_source' is added: 'golden' or 'llm_generated'
"""

import json
import asyncio
from typing import List, Dict, Any
from openai import AsyncAzureOpenAI

from Config.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_CHAT_COMPLETION_MODEL
)


class CropTranslationService:
    """Service to translate missing crop names using LLM."""

    def __init__(self):
        """Initialize Azure OpenAI client."""
        self.client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        self.model = AZURE_OPENAI_CHAT_COMPLETION_MODEL

    async def translate_crops_batch(
        self,
        crops_to_translate: List[Dict[str, Any]],
        existing_hebrew_crops: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Translate a batch of crops using LLM.

        Args:
            crops_to_translate: List of crops without Hebrew translation
                Each item: {'id': int, 'english': str}
            existing_hebrew_crops: Dictionary of crops with Hebrew translation
                Format: {id: {'id': int, 'english': str, 'hebrew': str}}

        Returns:
            Dictionary with translation suggestions
        """
        # Build the prompt
        prompt = self._build_translation_prompt(crops_to_translate, existing_hebrew_crops)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert agricultural translator specializing in English to Hebrew translation. "
                    "Your task is to translate crop names from English to Hebrew. "
                    "For each crop, you should either:\n"
                    "1. Map it to an existing Hebrew crop name if it's the same crop (e.g., 'Apples' -> existing 'תפוח עץ')\n"
                    "2. Suggest a new Hebrew translation if no matching crop exists\n\n"
                    "Always respond with valid JSON format."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Call LLM
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        # Parse response
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)

        return result

    def _build_translation_prompt(
        self,
        crops_to_translate: List[Dict[str, Any]],
        existing_hebrew_crops: Dict[int, Dict[str, Any]]
    ) -> str:
        """Build the prompt for LLM with crops to translate and existing Hebrew crops."""

        # Format existing Hebrew crops for reference
        existing_crops_text = "**Existing crops with Hebrew translations (ID: English - Hebrew):**\n\n"
        for crop_id, crop_data in existing_hebrew_crops.items():
            existing_crops_text += f"- ID {crop_id}: {crop_data['english']} - {crop_data['hebrew']}\n"

        # Format crops to translate
        crops_to_translate_text = "\n**Crops to translate (ID: English):**\n\n"
        for crop in crops_to_translate:
            crops_to_translate_text += f"- ID {crop['id']}: {crop['english']}\n"

        # Build full prompt
        prompt = f"""Below is a list of existing crops with their Hebrew translations, followed by a list of crops that need translation.

**CRITICAL RULE**: Crops that represent the same thing MUST receive the SAME Hebrew translation, even if they have slightly different English names (e.g., "Poppy seeds", "Poppy, seed 1", "Poppy, seed 2" are all the same and must get identical Hebrew translations). This ensures consistency and allows us to merge duplicate entries later.

{existing_crops_text}

{crops_to_translate_text}

**Instructions:**

For each crop in the "Crops to translate" list, you need to decide:

1. **Use existing Hebrew translation**: If the crop is essentially the same as an existing crop (considering synonyms, plural/singular forms, or different names for the same thing), use that crop's Hebrew translation.
   - Example: "Apples" is the same as "Apple" - use its Hebrew "תפוח עץ"
   - Example: "Tomatos" is the same as "Tomato" - use its Hebrew
   - Example: "Eggplant" and "Aubergine" are the same crop
   - Example: "Poppy seeds", "Poppy, seed 1", "Poppy, seed 2" are all the same crop - they should ALL use the same Hebrew translation
   - **CRITICAL**: If multiple crops in the current list refer to the same thing (e.g., "Poppy, seed 1" and "Poppy, seed 2"), they MUST get the same Hebrew translation. Do NOT create separate translations for variations of the same crop.
   - IMPORTANT: The crop will keep its ORIGINAL ID, only the Hebrew translation will be copied

2. **New translation**: If the crop is genuinely different and doesn't match any existing crop, provide a new Hebrew translation.
   - Use proper Hebrew agricultural terminology
   - Be consistent with the style of existing Hebrew names
   - **CRITICAL**: Before creating a new translation, check if another crop in the CURRENT LIST is essentially the same thing. If so, use the SAME Hebrew translation for both.

**Output Format:**

Return a JSON object with the following structure:

{{
  "translations": [
    {{
      "id": <crop_id>,
      "english": "<english_name>",
      "action": "use_existing_hebrew",
      "source_crop_id": <existing_crop_id>,
      "suggested_hebrew": "<hebrew_from_existing_crop>",
      "reasoning": "<brief explanation why they're the same crop>"
    }},
    {{
      "id": <crop_id>,
      "english": "<english_name>",
      "action": "new_translation",
      "suggested_hebrew": "<hebrew_translation>",
      "reasoning": "<brief explanation for the translation>"
    }}
  ]
}}

**Important:**
- Be conservative with mappings - only map if you're confident they're the same crop
- For new translations, use proper Hebrew without transliteration
- Provide clear reasoning for each decision
- Return valid JSON only, no additional text
"""

        return prompt


async def main():
    """Main function to process missing translations."""

    print("=" * 80)
    print("CROP TRANSLATION SERVICE - Missing Hebrew Translations")
    print("=" * 80)
    print()

    # Load golden mapping
    print("📂 Loading golden_mapping.json...")
    with open('golden_mapping.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    crops = mapping['crops']

    # Separate crops with and without Hebrew
    crops_with_hebrew = {}
    crops_without_hebrew = []

    for key, value in crops.items():
        # Skip non-numeric keys (these are the name->id mappings)
        if not isinstance(key, str) or not key.isdigit():
            continue

        crop_data = value
        if crop_data.get('hebrew'):
            crops_with_hebrew[int(key)] = crop_data
        else:
            crops_without_hebrew.append({
                'id': crop_data['id'],
                'english': crop_data['english']
            })

    print(f"✓ Found {len(crops_with_hebrew)} crops with Hebrew translation")
    print(f"✓ Found {len(crops_without_hebrew)} crops without Hebrew translation")
    print()

    if not crops_without_hebrew:
        print("🎉 All crops already have Hebrew translations!")
        return

    # Initialize translation service
    print("🤖 Initializing Azure OpenAI translation service...")
    service = CropTranslationService()
    print("✓ Service initialized")
    print()

    # Process in chunks (to avoid token limits)
    CHUNK_SIZE = 50  # Adjust based on your token limits
    all_suggestions = []

    # Keep a running list of Hebrew translations that includes newly translated crops
    # This ensures LLM sees all previously translated crops when processing new chunks
    current_hebrew_crops = crops_with_hebrew.copy()

    total_chunks = (len(crops_without_hebrew) + CHUNK_SIZE - 1) // CHUNK_SIZE

    for i in range(0, len(crops_without_hebrew), CHUNK_SIZE):
        chunk = crops_without_hebrew[i:i + CHUNK_SIZE]
        chunk_num = i // CHUNK_SIZE + 1

        print(f"📝 Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} crops)...")

        try:
            # Pass the growing list of Hebrew translations
            result = await service.translate_crops_batch(chunk, current_hebrew_crops)

            if 'translations' in result:
                translations = result['translations']
                all_suggestions.extend(translations)
                print(f"   ✓ Received {len(translations)} suggestions")

                # Add newly translated crops to current_hebrew_crops
                # so they're visible to the LLM in the next chunk
                for translation in translations:
                    crop_id = translation.get('id')
                    english_name = translation.get('english')
                    suggested_hebrew = translation.get('suggested_hebrew')

                    if crop_id and english_name and suggested_hebrew:
                        current_hebrew_crops[crop_id] = {
                            'id': crop_id,
                            'english': english_name,
                            'hebrew': suggested_hebrew
                        }
            else:
                print(f"   ⚠ Warning: Unexpected response format from LLM")
                print(f"   Response: {result}")

        except Exception as e:
            print(f"   ❌ Error processing chunk: {e}")
            continue

    print()
    print(f"✓ Processed {len(all_suggestions)} crop translations")
    print()

    # Analyze results
    use_existing_count = sum(1 for s in all_suggestions if s.get('action') == 'use_existing_hebrew')
    new_translation_count = sum(1 for s in all_suggestions if s.get('action') == 'new_translation')

    print("📊 Summary:")
    print(f"   - Using existing Hebrew translations: {use_existing_count}")
    print(f"   - New translations suggested: {new_translation_count}")
    print()

    # Save suggestions to file
    output = {
        'metadata': {
            'total_crops_processed': len(crops_without_hebrew),
            'suggestions_generated': len(all_suggestions),
            'using_existing_hebrew': use_existing_count,
            'new_translations': new_translation_count,
            'timestamp': None  # Could add datetime here
        },
        'suggestions': all_suggestions
    }

    output_file = 'translation_suggestions.json'
    print(f"💾 Saving suggestions to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✓ Saved to {output_file}")
    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("1. Review the suggestions in translation_suggestions.json")
    print("2. Edit the file to approve/modify translations")
    print("3. Run apply_translations.py to create golden_mapping_expanded.json")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
