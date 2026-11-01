from pathlib import Path
import pandas as pd

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg")
out = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"

files = sorted(
    p for p in root.rglob("*")
    if p.is_file() and p.suffix.lower() in {".csv", ".xlsx", ".xls"}
)

print("=== HCC METADATA FILES ===")
for path in files:
    print(f"\nFILE: {path}")
    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path, nrows=5)
            full_df = pd.read_csv(path)
            print("Rows:", len(full_df))
            print("Columns:", list(full_df.columns))
            print("Sample:")
            print(df.head(3).to_string(index=False))
        else:
            book = pd.ExcelFile(path)
            print("Sheets:", book.sheet_names)
            for sheet in book.sheet_names:
                df = pd.read_excel(path, sheet_name=sheet, nrows=5)
                print(f"\nSheet: {sheet}")
                print("Columns:", list(df.columns))
                print(df.head(3).to_string(index=False))
    except Exception as exc:
        print("READ ERROR:", repr(exc))

print("\n=== PATIENT FOLDER COUNTS ===")
patient_dirs = sorted(
    p for p in root.rglob("*")
    if p.is_dir() and p.name.upper().startswith("HCC_")
)
print("Directories with names starting HCC_:", len(patient_dirs))
print("First 15:")
for p in patient_dirs[:15]:
    print(p.relative_to(root))
