from pathlib import Path
import pandas as pd

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC")
out = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit")

metadata_path = root / "metadata" / "metadata.csv"
status_path = root / "metadata" / "completion_status.csv"

if not metadata_path.is_file():
    raise FileNotFoundError(f"Metadata not found: {metadata_path}")

meta = pd.read_csv(metadata_path, low_memory=False)

print("=== NEW DOWNLOAD: METADATA AUDIT ===")
print("Metadata rows:", len(meta))
print("Unique SeriesInstanceUIDs:", meta["SeriesInstanceUID"].nunique())
print("Unique PatientIDs:", meta["PatientID"].nunique())
print("\n=== MODALITY COUNTS ===")
print(meta["Modality"].fillna("<missing>").value_counts().to_string())

if status_path.is_file():
    status = pd.read_csv(status_path, low_memory=False)
    print("\n=== DOWNLOAD STATUS ===")
    print("Status rows:", len(status))
    print("Unique status SeriesInstanceUIDs:", status["SeriesInstanceUID"].nunique())

    df = meta.merge(
        status,
        on="SeriesInstanceUID",
        how="left",
        suffixes=("", "_status"),
        indicator=True
    )

    print("Metadata series with status:", int((df["_merge"] == "both").sum()))
    print("Metadata series without status:", int((df["_merge"] != "both").sum()))

    status_columns = [
        c for c in df.columns
        if "status" in c.lower() or "complete" in c.lower()
    ]
    for col in status_columns:
        print(f"\n{col}:")
        print(df[col].fillna("<missing>").value_counts().head(15).to_string())

    df.to_csv(out / "hcc_series_inventory_joined_new_download.csv", index=False)
else:
    print("\ncompletion_status.csv not found; metadata-only audit.")

ct = meta[meta["Modality"].astype(str).str.upper().eq("CT")].copy()
seg = meta[meta["Modality"].astype(str).str.upper().eq("SEG")].copy()

print("\n=== CT AND SEG EXPECTATIONS ===")
print("CT metadata series:", len(ct))
print("SEG metadata series:", len(seg))
print("Patients with CT metadata:", ct["PatientID"].nunique())
print("Patients with SEG metadata:", seg["PatientID"].nunique())

ct.to_csv(out / "hcc_ct_series_candidates_new_download.csv", index=False)
seg.to_csv(out / "hcc_seg_series_candidates_new_download.csv", index=False)

print("\nReports saved in:", out)
