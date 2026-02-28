import pandas as pd

excel_path = "d:/item/ProSourcing/template.xlsx"

try:
    xl = pd.ExcelFile(excel_path)
    print("Sheets found:", xl.sheet_names)
    
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        print(f"\n--- Sheet: {sheet} ---")
        print("Columns:", df.columns.tolist())
        # Print first few rows to understand structure
        print("First few rows:")
        print(df.head(2).to_dict(orient='records'))
except Exception as e:
    print(f"Error reading Excel: {e}")
