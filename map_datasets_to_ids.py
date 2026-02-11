"""
Map dataset entries to crop and pesticide IDs with caching.

This script:
1. Loads crops.json and pesticides.json (the reference lists with IDs)
2. Loads each dataset (IL, EU, CODEX)
3. Maps entries:
   - Israeli dataset: Direct exact matching (no LLM needed)
   - Other datasets (EU, CODEX): LLM-based mapping with fuzzy matching and caching
4. Caching mechanism:
   - Checks cache before calling LLM to avoid redundant API calls
   - Saves mappings to cache file per dataset
   - Significantly reduces cost for large datasets with repetitive entries
5. Adds 6 new columns to each dataset:
   - crop_id_mapping: The matched crop ID(s) or None if no match
   - crop_name_mapping: The matched crop name(s) or None if no match
   - crop_reasoning: Explanation in Hebrew (always filled)
   - pesticide_id_mapping: The matched pesticide ID(s) or None if no match
   - pesticide_name_mapping: The matched pesticide name(s) or None if no match
   - pesticide_reasoning: Explanation in Hebrew (always filled)
6. Saves the enriched datasets

Israeli dataset reasoning: "התאמה מדויקת" for exact matches.
Other datasets: LLM provides Hebrew explanation.
If no mapping found, ID and name are None but reasoning explains why (in Hebrew).
"""

import json
import pandas as pd
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from openai import AsyncAzureOpenAI

from Config.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_CHAT_COMPLETION_MODEL
)


class DatasetMappingService:
    """Service to map dataset entries to crop and pesticide IDs using LLM with caching."""

    def __init__(self, crops_list: List[Dict], pesticides_list: List[Dict], cache_path: Path = None):
        """
        Initialize the mapping service.

        Args:
            crops_list: List of crops with id, name_he, name_en
            pesticides_list: List of pesticides with id, name
            cache_path: Optional path to cache file for storing mappings
        """
        self.client = AsyncAzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        self.model = AZURE_OPENAI_CHAT_COMPLETION_MODEL
        self.crops_list = crops_list
        self.pesticides_list = pesticides_list
        self.cache_path = cache_path
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cache from file if exists."""
        if self.cache_path and self.cache_path.exists():
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"crops": {}, "pesticides": {}}

    def _save_cache(self):
        """Save cache to file."""
        if self.cache_path:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get_cached_mapping(self, name: str, mapping_type: str) -> Dict:
        """
        Get cached mapping if exists.

        Args:
            name: Name to look up (crop or pesticide)
            mapping_type: 'crops' or 'pesticides'

        Returns:
            Cached mapping dict or None
        """
        return self.cache.get(mapping_type, {}).get(name)

    def add_to_cache(self, name: str, mapping_type: str, mapping_data: Dict):
        """
        Add mapping to cache.

        Args:
            name: Name to cache (crop or pesticide)
            mapping_type: 'crops' or 'pesticides'
            mapping_data: Mapping data with ids, names, reasoning
        """
        if mapping_type not in self.cache:
            self.cache[mapping_type] = {}
        self.cache[mapping_type][name] = mapping_data

    async def map_batch(
        self,
        batch_entries: List[Dict[str, Any]],
        dataset_language: str
    ) -> Dict[str, Any]:
        """
        Map a batch of dataset entries to IDs.

        Args:
            batch_entries: List of entries to map
                Each entry: {'crop_name': str, 'pesticide_name': str, 'row_index': int}
            dataset_language: 'he' for Hebrew, 'en' for English, 'mixed' for both

        Returns:
            Dictionary with mapping results
        """
        prompt = self._build_mapping_prompt(batch_entries, dataset_language)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert agricultural data mapper. "
                    "Your task is to match crop and pesticide names from datasets "
                    "to standardized IDs from reference lists. "
                    "Consider synonyms, translations, spelling variations, and common names. "
                    "If multiple matches are possible, return all of them with explanations. "
                    "IMPORTANT: All reasoning explanations MUST be in Hebrew. "
                    "Always respond with valid JSON format."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content or "{}"
        result = json.loads(content)

        return result

    def _build_mapping_prompt(
        self,
        batch_entries: List[Dict[str, Any]],
        dataset_language: str
    ) -> str:
        """Build the prompt for LLM with entries to map and reference lists."""

        # Format reference crops list
        crops_ref_text = "**Reference Crops List (ID: Hebrew - English):**\n\n"
        for crop in self.crops_list:
            crops_ref_text += f"- ID {crop['id']}: {crop['name_he']} - {crop['name_en']}\n"

        # Format reference pesticides list
        pesticides_ref_text = "\n**Reference Pesticides List (ID: Name):**\n\n"
        for pesticide in self.pesticides_list:
            pesticides_ref_text += f"- ID {pesticide['id']}: {pesticide['name']}\n"

        # Format entries to map
        entries_text = "\n**Dataset Entries to Map:**\n\n"
        for entry in batch_entries:
            entries_text += f"- Row {entry['row_index']}: Crop=\"{entry['crop_name']}\", Pesticide=\"{entry['pesticide_name']}\"\n"

        prompt = f"""You have reference lists of crops and pesticides with unique IDs.
Your task is to map dataset entries to these reference IDs.

{crops_ref_text}

{pesticides_ref_text}

{entries_text}

**Dataset Language:** {dataset_language}

**Instructions:**

For each dataset entry, you need to:

1. **Map the crop name** to one or more crop IDs from the reference list:
   - Consider exact matches, synonyms, plural/singular forms
   - For Hebrew datasets, match Hebrew names; for English, match English names
   - If multiple crops could match, return all possibilities
   - Provide clear reasoning for your choice

2. **Map the pesticide name** to one or more pesticide IDs from the reference list:
   - Consider exact matches, chemical name variations, common names
   - Pesticide names are in English in both datasets
   - If multiple pesticides could match, return all possibilities
   - Provide clear reasoning for your choice

**Output Format:**

Return a JSON object with this structure:

{{
  "mappings": [
    {{
      "row_index": <row_index>,
      "crop_mapping": {{
        "ids": [<crop_id>] or [<crop_id1>, <crop_id2>, ...],
        "reasoning": "<explanation for the crop match>"
      }},
      "pesticide_mapping": {{
        "ids": [<pesticide_id>] or [<pesticide_id1>, <pesticide_id2>, ...],
        "reasoning": "<explanation for the pesticide match>"
      }}
    }}
  ]
}}

**Important:**
- Return only valid JSON, no additional text
- Use empty array [] if no match is found
- Be conservative but reasonable with mappings
- CRITICAL: All reasoning MUST be written in Hebrew (עברית)
- Provide clear, concise reasoning (1-2 sentences in Hebrew)
- If uncertain between multiple options, include all with explanation in Hebrew
- If no match found, explain why in Hebrew
"""

        return prompt


async def process_dataset(
    dataset_path: Path,
    dataset_name: str,
    crop_col: str,
    pesticide_col: str,
    language: str,
    crops_list: List[Dict],
    pesticides_list: List[Dict],
    output_path: Path,
    chunk_size: int = 20,
    limit_rows: int = None,
    is_israeli: bool = False
):
    """
    Process a single dataset and add mapping columns.

    Args:
        dataset_path: Path to the CSV file
        dataset_name: Name of the dataset (for logging)
        crop_col: Name of the crop column
        pesticide_col: Name of the pesticide column
        language: 'he' for Hebrew, 'en' for English
        crops_list: Reference crops list
        pesticides_list: Reference pesticides list
        output_path: Where to save the enriched dataset
        chunk_size: Number of rows to process per LLM call
        limit_rows: Optional limit for number of rows to process (for testing)
        is_israeli: If True, use direct mapping without LLM (Israeli dataset only)
    """
    print(f"\n{'=' * 70}")
    print(f"Processing {dataset_name} dataset")
    print(f"{'=' * 70}")

    # Load dataset
    print(f"Loading dataset: {dataset_path}")
    df = pd.read_csv(dataset_path, encoding='utf-8-sig')
    print(f"Loaded {len(df)} rows")

    # Limit rows if specified (for testing)
    if limit_rows:
        df = df.head(limit_rows)
        print(f"Limited to first {limit_rows} rows for testing")

    # Initialize new columns
    df['crop_id_mapping'] = None
    df['crop_name_mapping'] = None
    df['crop_reasoning'] = None
    df['pesticide_id_mapping'] = None
    df['pesticide_name_mapping'] = None
    df['pesticide_reasoning'] = None

    # For Israeli dataset, do direct mapping without LLM
    if is_israeli:
        print("Direct mapping for Israeli dataset (no LLM needed)...")

        # Create lookup dictionaries for fast mapping
        crop_lookup_he = {c['name_he']: c for c in crops_list}
        pesticide_lookup = {p['name']: p for p in pesticides_list}

        for i in range(len(df)):
            crop_name = str(df.iloc[i][crop_col]) if pd.notna(df.iloc[i][crop_col]) else ''
            pesticide_name = str(df.iloc[i][pesticide_col]) if pd.notna(df.iloc[i][pesticide_col]) else ''

            # Map crop
            crop_obj = crop_lookup_he.get(crop_name)
            if crop_obj:
                df.at[i, 'crop_id_mapping'] = crop_obj['id']
                df.at[i, 'crop_name_mapping'] = crop_obj['name_he']
                df.at[i, 'crop_reasoning'] = 'התאמה מדויקת'
            else:
                df.at[i, 'crop_reasoning'] = f'לא נמצאה התאמה עבור "{crop_name}"'

            # Map pesticide
            pesticide_obj = pesticide_lookup.get(pesticide_name)
            if pesticide_obj:
                df.at[i, 'pesticide_id_mapping'] = pesticide_obj['id']
                df.at[i, 'pesticide_name_mapping'] = pesticide_obj['name']
                df.at[i, 'pesticide_reasoning'] = 'התאמה מדויקת'
            else:
                df.at[i, 'pesticide_reasoning'] = f'לא נמצאה התאמה עבור "{pesticide_name}"'

        print(f"Completed direct mapping for {len(df)} rows")

    else:
        # Use LLM for non-Israeli datasets with caching
        print("Initializing mapping service with cache...")

        # Create cache file path
        cache_file = output_path.parent / f"{dataset_name}_mapping_cache.json"
        service = DatasetMappingService(crops_list, pesticides_list, cache_path=cache_file)

        # Process in chunks
        total_chunks = (len(df) + chunk_size - 1) // chunk_size

        # Statistics tracking
        crop_cache_hits = 0
        pesticide_cache_hits = 0
        crops_sent_to_llm = 0
        pesticides_sent_to_llm = 0
        llm_calls = 0

        for chunk_idx in range(0, len(df), chunk_size):
            chunk_end = min(chunk_idx + chunk_size, len(df))
            chunk_num = chunk_idx // chunk_size + 1

            print(f"\nProcessing chunk {chunk_num}/{total_chunks} (rows {chunk_idx}-{chunk_end-1})...")

            # Prepare batch entries and check cache
            row_data = []
            unique_crops_needed = set()
            unique_pesticides_needed = set()

            for i in range(chunk_idx, chunk_end):
                crop_name = str(df.iloc[i][crop_col]) if pd.notna(df.iloc[i][crop_col]) else ''
                pesticide_name = str(df.iloc[i][pesticide_col]) if pd.notna(df.iloc[i][pesticide_col]) else ''

                # Check cache for crop
                crop_cached = service.get_cached_mapping(crop_name, 'crops')
                if crop_cached:
                    crop_cache_hits += 1
                    df.at[i, 'crop_id_mapping'] = crop_cached.get('id')
                    df.at[i, 'crop_name_mapping'] = crop_cached.get('name')
                    df.at[i, 'crop_reasoning'] = crop_cached.get('reasoning')
                elif crop_name:
                    unique_crops_needed.add(crop_name)

                # Check cache for pesticide
                pesticide_cached = service.get_cached_mapping(pesticide_name, 'pesticides')
                if pesticide_cached:
                    pesticide_cache_hits += 1
                    df.at[i, 'pesticide_id_mapping'] = pesticide_cached.get('id')
                    df.at[i, 'pesticide_name_mapping'] = pesticide_cached.get('name')
                    df.at[i, 'pesticide_reasoning'] = pesticide_cached.get('reasoning')
                elif pesticide_name:
                    unique_pesticides_needed.add(pesticide_name)

                # Store row data for later mapping
                row_data.append({
                    'row_index': i,
                    'crop_name': crop_name,
                    'pesticide_name': pesticide_name,
                    'crop_cached': bool(crop_cached),
                    'pesticide_cached': bool(pesticide_cached)
                })

            # Skip LLM call if everything was cached
            if not unique_crops_needed and not unique_pesticides_needed:
                print(f"All entries cached, skipping LLM call")
                continue

            # Create batch with unique items only
            batch_entries = []
            batch_idx = 0
            for crop_name in unique_crops_needed:
                batch_entries.append({
                    'row_index': batch_idx,
                    'crop_name': crop_name,
                    'pesticide_name': '',
                    'crop_cached': False,
                    'pesticide_cached': True
                })
                batch_idx += 1
                crops_sent_to_llm += 1

            for pesticide_name in unique_pesticides_needed:
                batch_entries.append({
                    'row_index': batch_idx,
                    'crop_name': '',
                    'pesticide_name': pesticide_name,
                    'crop_cached': True,
                    'pesticide_cached': False
                })
                batch_idx += 1
                pesticides_sent_to_llm += 1

            print(f"Cache hits: {crop_cache_hits + pesticide_cache_hits}, Calling LLM for {len(batch_entries)} entries")
            llm_calls += 1

            try:
                # Get mappings from LLM
                result = await service.map_batch(batch_entries, language)

                if 'mappings' in result:
                    mappings = result['mappings']
                    print(f"Received {len(mappings)} mappings")

                    # Create temporary mapping dictionaries
                    crop_mappings_temp = {}
                    pesticide_mappings_temp = {}

                    # Process LLM results and add to temporary mappings
                    for mapping in mappings:
                        batch_idx = mapping['row_index']
                        entry = batch_entries[batch_idx]

                        # Process crop mapping (if not cached)
                        if not entry.get('crop_cached') and entry['crop_name']:
                            crop_name = entry['crop_name']
                            crop_map = mapping.get('crop_mapping', {})
                            crop_ids = crop_map.get('ids', [])
                            crop_reasoning = crop_map.get('reasoning', '')

                            # Find crop names from IDs
                            crop_names = []
                            if crop_ids:
                                for crop_id in crop_ids:
                                    crop_obj = next((c for c in crops_list if c['id'] == crop_id), None)
                                    if crop_obj:
                                        if language == 'he':
                                            crop_names.append(crop_obj['name_he'])
                                        else:
                                            crop_names.append(crop_obj['name_en'])

                            # Store values
                            crop_id_val = json.dumps(crop_ids) if len(crop_ids) > 1 else (crop_ids[0] if crop_ids else None)
                            crop_name_val = json.dumps(crop_names, ensure_ascii=False) if len(crop_names) > 1 else (crop_names[0] if crop_names else None)

                            crop_mappings_temp[crop_name] = {
                                'id': crop_id_val,
                                'name': crop_name_val,
                                'reasoning': crop_reasoning
                            }

                            # Add to cache
                            service.add_to_cache(crop_name, 'crops', crop_mappings_temp[crop_name])

                        # Process pesticide mapping (if not cached)
                        if not entry.get('pesticide_cached') and entry['pesticide_name']:
                            pesticide_name = entry['pesticide_name']
                            pesticide_map = mapping.get('pesticide_mapping', {})
                            pesticide_ids = pesticide_map.get('ids', [])
                            pesticide_reasoning = pesticide_map.get('reasoning', '')

                            # Find pesticide names from IDs
                            pesticide_names = []
                            if pesticide_ids:
                                for pesticide_id in pesticide_ids:
                                    pesticide_obj = next((p for p in pesticides_list if p['id'] == pesticide_id), None)
                                    if pesticide_obj:
                                        pesticide_names.append(pesticide_obj['name'])

                            # Store values
                            pesticide_id_val = json.dumps(pesticide_ids) if len(pesticide_ids) > 1 else (pesticide_ids[0] if pesticide_ids else None)
                            pesticide_name_val = json.dumps(pesticide_names, ensure_ascii=False) if len(pesticide_names) > 1 else (pesticide_names[0] if pesticide_names else None)

                            pesticide_mappings_temp[pesticide_name] = {
                                'id': pesticide_id_val,
                                'name': pesticide_name_val,
                                'reasoning': pesticide_reasoning
                            }

                            # Add to cache
                            service.add_to_cache(pesticide_name, 'pesticides', pesticide_mappings_temp[pesticide_name])

                    # Apply mappings to all relevant rows
                    for row_info in row_data:
                        row_idx = row_info['row_index']

                        # Apply crop mapping if needed
                        if not row_info['crop_cached'] and row_info['crop_name'] in crop_mappings_temp:
                            crop_data = crop_mappings_temp[row_info['crop_name']]
                            df.at[row_idx, 'crop_id_mapping'] = crop_data['id']
                            df.at[row_idx, 'crop_name_mapping'] = crop_data['name']
                            df.at[row_idx, 'crop_reasoning'] = crop_data['reasoning']

                        # Apply pesticide mapping if needed
                        if not row_info['pesticide_cached'] and row_info['pesticide_name'] in pesticide_mappings_temp:
                            pesticide_data = pesticide_mappings_temp[row_info['pesticide_name']]
                            df.at[row_idx, 'pesticide_id_mapping'] = pesticide_data['id']
                            df.at[row_idx, 'pesticide_name_mapping'] = pesticide_data['name']
                            df.at[row_idx, 'pesticide_reasoning'] = pesticide_data['reasoning']

                    print(f"Applied mappings to dataframe and updated cache")
                else:
                    print(f"Warning: Unexpected response format from LLM")
                    print(f"Response: {result}")

            except Exception as e:
                print(f"Error processing chunk: {e}")
                continue

        # Save cache
        print(f"\nSaving cache with {len(service.cache['crops'])} crops and {len(service.cache['pesticides'])} pesticides")
        service._save_cache()
        print(f"Cache saved to: {cache_file}")

        # Print detailed statistics
        print("\n" + "-" * 70)
        print("Statistics:")
        print(f"  Total LLM calls: {llm_calls}")
        print(f"  Crops:")
        print(f"    - Sent to LLM: {crops_sent_to_llm}")
        print(f"    - Retrieved from cache: {crop_cache_hits}")
        print(f"    - Total processed: {crops_sent_to_llm + crop_cache_hits}")
        if crop_cache_hits > 0:
            print(f"    - Cache savings: {crop_cache_hits / (crops_sent_to_llm + crop_cache_hits) * 100:.1f}%")
        print(f"  Pesticides:")
        print(f"    - Sent to LLM: {pesticides_sent_to_llm}")
        print(f"    - Retrieved from cache: {pesticide_cache_hits}")
        print(f"    - Total processed: {pesticides_sent_to_llm + pesticide_cache_hits}")
        if pesticide_cache_hits > 0:
            print(f"    - Cache savings: {pesticide_cache_hits / (pesticides_sent_to_llm + pesticide_cache_hits) * 100:.1f}%")
        print("-" * 70)

    # Save enriched dataset
    print(f"\nSaving enriched dataset to: {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Saved successfully")

    print(f"\n{'=' * 70}")
    print(f"Completed {dataset_name} dataset")
    print(f"{'=' * 70}")


async def main():
    """Main function to process all datasets."""

    print("=" * 70)
    print("Dataset Mapping to IDs - Using LLM")
    print("=" * 70)

    # Load reference lists
    print("\nLoading reference lists...")

    crops_path = Path("output/crops.json")
    pesticides_path = Path("output/pesticides.json")

    with open(crops_path, 'r', encoding='utf-8') as f:
        crops_list = json.load(f)
    print(f"Loaded {len(crops_list)} crops")

    with open(pesticides_path, 'r', encoding='utf-8') as f:
        pesticides_list = json.load(f)
    print(f"Loaded {len(pesticides_list)} pesticides")

    # Create output directory
    output_dir = Path("output/mapped_datasets")
    output_dir.mkdir(exist_ok=True, parents=True)

    # Testing mode: limit to 5 rows
    TEST_MODE = False
    TEST_ROWS = 5

    # Process IL dataset (Hebrew) - Direct mapping without LLM
    await process_dataset(
        dataset_path=Path("Datasets/IL/IL_He.csv"),
        dataset_name="Israeli (Hebrew)",
        crop_col="גידול",
        pesticide_col="חומר פעיל",
        language="he",
        crops_list=crops_list,
        pesticides_list=pesticides_list,
        output_path=output_dir / "IL_He_with_ids.csv",
        chunk_size=20,
        limit_rows=TEST_ROWS if TEST_MODE else None,
        is_israeli=True
    )

    # Process EU dataset (English)
    await process_dataset(
        dataset_path=Path("Datasets/EU/EU_MRL_Final_Database.csv"),
        dataset_name="EU",
        crop_col="Crop",
        pesticide_col="Pesticide",
        language="en",
        crops_list=crops_list,
        pesticides_list=pesticides_list,
        output_path=output_dir / "EU_with_ids.csv",
        chunk_size=20,
        limit_rows=TEST_ROWS if TEST_MODE else None
    )

    # Process CODEX dataset (English)
    await process_dataset(
        dataset_path=Path("Datasets/CODEX/codex_mrls_enhanced.csv"),
        dataset_name="CODEX",
        crop_col="Commodity_Name",
        pesticide_col="Pesticide_Name",
        language="en",
        crops_list=crops_list,
        pesticides_list=pesticides_list,
        output_path=output_dir / "CODEX_with_ids.csv",
        chunk_size=20,
        limit_rows=TEST_ROWS if TEST_MODE else None
    )

    print("\n" + "=" * 70)
    print("All datasets processed successfully!")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  - {output_dir / 'IL_He_with_ids.csv'}")
    print(f"  - {output_dir / 'EU_with_ids.csv'}")
    print(f"  - {output_dir / 'CODEX_with_ids.csv'}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
