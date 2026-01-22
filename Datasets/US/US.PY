import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import time
import re
import sys

# --- הגדרות ---
BASE_URL = "https://www.law.cornell.edu/cfr/text/40/part-180/subpart-C"
BASE_CHEMICAL_URL = "https://www.law.cornell.edu/cfr/text/40/"

def get_all_chemical_ids():
    """
    שלב 1: הולך לתוכן העניינים ומוציא את רשימת כל הכימיקלים והמספרים שלהם.
    """
    print(f"Scanning Table of Contents at {BASE_URL}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(BASE_URL, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Critical Error fetching index: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # מוצאים את כל הלינקים שמתחילים ב "180."
    chemicals = []
    # Cornell structure usually lists sections in a specific div or list
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link['href']
        text = link.get_text().strip()
        
        # חיפוש תבנית של סעיף רלוונטי (למשל 180.123)
        match = re.search(r'180\.(\d+)', text)
        if match and "tolerances" in text.lower():
            # ניקוי שם הכימיקל מהטקסט
            # דוגמה: "40 CFR § 180.106 - Diuron; tolerances for residues."
            # אנחנו רוצים רק "Diuron"
            clean_name = text.split('-')[-1].split(';')[0].strip()
            if "CFR" in clean_name: # Fallback cleaning
                clean_name = text
                
            section_id = f"180.{match.group(1)}"
            
            chemicals.append({
                "name": clean_name,
                "id": section_id
            })
            
    # סינון כפילויות (לפעמים יש לינקים כפולים באותו דף)
    unique_chems = {v['id']: v for v in chemicals}.values()
    print(f"Found {len(unique_chems)} chemicals to process.")
    return list(unique_chems)

def fetch_single_chemical(chem_info):
    """
    שלב 2: נכנס לדף ספציפי ושולף את טבלת ה-MRL
    """
    url = f"{BASE_CHEMICAL_URL}{chem_info['id']}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            try:
                # שימוש ב-StringIO למניעת אזהרות
                html_content = io.StringIO(str(table))
                df = pd.read_html(html_content)[0]
                
                # זיהוי אם זו טבלת MRL (חייבת להכיל עמודת Commodities ו-Million)
                cols_str = " ".join([str(c).lower() for c in df.columns])
                
                if "modity" in cols_str and ("parts per million" in cols_str or "ppm" in cols_str):
                    # נרמול שמות עמודות (לפעמים זה 'Commodity', לפעמים 'Commodities')
                    # נניח שעמודה 0 היא השם ועמודה 1 היא המספר
                    clean_df = df.iloc[:, [0, 1]].copy()
                    clean_df.columns = ['Commodity', 'MRL_ppm']
                    
                    # ניקוי וסידור
                    clean_df['Chemical_Name'] = chem_info['name']
                    clean_df['Section_ID'] = chem_info['id']
                    
                    # המרת המספרים (טיפול ב-"Null" או טקסט)
                    clean_df['MRL_ppm'] = pd.to_numeric(clean_df['MRL_ppm'], errors='coerce')
                    
                    return clean_df
            except Exception:
                continue
                
    except Exception as e:
        print(f"Error fetching {chem_info['name']}: {e}")
        return None
        
    return None

def main():
    # 1. השגת הרשימה
    chemicals = get_all_chemical_ids()
    
    if not chemicals:
        print("No chemicals found. Check internet connection or URL.")
        return

    all_data = []
    
    # 2. לולאה ראשית
    print(f"Starting scraping process for {len(chemicals)} chemicals...")
    print("This will take time. Progress will be saved automatically.")
    
    for i, chem in enumerate(chemicals):
        # הדפסת התקדמות כל 10 חומרים
        if i % 10 == 0:
            print(f"Processing {i}/{len(chemicals)}: {chem['name']}...")
            
        df = fetch_single_chemical(chem)
        if df is not None and not df.empty:
            all_data.append(df)
            
        # השהייה מנומסת כדי לא להעמיס על השרת (חשוב!)
        time.sleep(0.5)

    # 3. שמירת תוצאות
    if all_data:
        print("Combining data...")
        full_df = pd.concat(all_data, ignore_index=True)
        
        # שמירת פורמט ארוך (בסיס נתונים)
        full_df.to_csv("full_pesticide_database_long.csv", index=False, encoding='utf-8-sig')
        print("Saved 'full_pesticide_database_long.csv'")
        
        # יצירת המטריצה (Pivot) - מה שביקשת
        # שורות = גידולים, עמודות = חומרים
        print("Creating Matrix pivot table...")
        matrix = full_df.pivot_table(
            index='Commodity',
            columns='Chemical_Name',
            values='MRL_ppm',
            aggfunc='max' # במקרה של כפילות לוקחים את המחמיר (או המקסימלי, תלוי בהגדרתך)
        )
        
        matrix.to_csv("full_pesticide_matrix.csv", encoding='utf-8-sig')
        print(f"Success! Saved Matrix with {len(matrix)} crops and {len(matrix.columns)} chemicals to 'full_pesticide_matrix.csv'")
        
    else:
        print("No MRL data could be extracted.")

if __name__ == "__main__":
    main()
