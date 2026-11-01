from pathlib import Path
import pandas as pd

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg")
out = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"

metadata_path = root / "metadata" / "metadata.csv"
status_path = root / "metadata" / "completion_status.csv"

meta = pd.read_csv(metadata_path, low_memory=False)
status = pd.read_csv(status_path, low_memory=False)

# Join series completion information by SeriesInstanceUID.
df = meta.merge(
    status,
    on="SeriesInstanceUID",
    how="left",
    suffixes=("", "_status"),
    indicator=True
)

print("=== BASIC COUNTS ===")
print("Metadata rows:", len(meta))
print("Unique SeriesInstanceUIDs:", meta["SeriesInstanceUID"].nunique())
print("Unique PatientIDs:", meta["PatientID"].nunique())
print("Completion status matched:", int((df["_merge"] == "both").sum()))
print("Completion status missing:", int((df["_merge"] != "both").sum()))

print("\n=== MODALITY COUNTS ===")
print(df["Modality"].fillna("<missing>").value_counts().to_string())

print("\n=== SERIES DESCRIPTION COUNTS ===")
print(
    df.groupby(
        ["Modality", "SeriesDescription"],
        dropna=False
    ).size().sort_values(ascending=False).head(40).to_string()
)

# CT records and SEG records, without assuming a specific phase is correct.
ct = df[df["Modality"].astype(str).str.upper().eq("CT")].copy()
seg = df[df["Modality"].astype(str).str.upper().eq("SEG")].copy()

print("\n=== CT AND SEG RECORDS ===")
print("CT series records:", len(ct))
print("Unique patients with CT records:", ct["PatientID"].nunique())
print("SEG series records:", len(seg))
print("Unique patients with SEG records:", seg["PatientID"].nunique())

ct_patients = set(ct["PatientID"].dropna().astype(str))
seg_patients = set(seg["PatientID"].dropna().astype(str))
print("Patients with both CT and SEG metadata:", len(ct_patients & seg_patients))
print("Patients with CT but no SEG metadata:", len(ct_patients - seg_patients))
print("Patients with SEG but no CT metadata:", len(seg_patients - ct_patients))

# Save full joined inventory and smaller useful subsets.
df.to_csv(out / "hcc_series_inventory_joined.csv", index=False)
ct.to_csv(out / "hcc_ct_series_candidates.csv", index=False)
seg.to_csv(out / "hcc_seg_series_candidates.csv", index=False)

# Compact per-patient counts for further inspection.
patient_summary = df.groupby("PatientID", dropna=False).agg(
    series_records=("SeriesInstanceUID", "nunique"),
    modalities=("Modality", lambda x: ",".join(sorted(
        set(str(v) for v in x.dropna())
    ))),
    completion_values=("completion_status", lambda x: ",".join(sorted(
        set(str(v) for v in x.dropna())
    )))
).reset_index()

patient_summary.to_csv(out / "hcc_patient_series_summary.csv", index=False)

print("\n=== SAVED REPORTS ===")
for name in [
    "hcc_series_inventory_joined.csv",
    "hcc_ct_series_candidates.csv",
    "hcc_seg_series_candidates.csv",
    "hcc_patient_series_summary.csv"
]:
    print(out / name)

print("\n=== SAMPLE CT CANDIDATES ===")
cols = [
    c for c in [
        "PatientID", "SeriesDescription", "BodyPartExamined",
        "ImageCount", "SliceThickness(mm)", "PixelSpacing(mm)-Row",
        "completion_status", "S5cmdManifestPath"
    ] if c in ct.columns
]
print(ct[cols].head(12).to_string(index=False))

print("\n=== SAMPLE SEGMENTATION CANDIDATES ===")
cols = [
    c for c in [
        "PatientID", "SeriesDescription", "Modality",
        "SeriesInstanceUID", "completion_status", "S5cmdManifestPath"
    ] if c in seg.columns
]
print(seg[cols].head(12).to_string(index=False))
