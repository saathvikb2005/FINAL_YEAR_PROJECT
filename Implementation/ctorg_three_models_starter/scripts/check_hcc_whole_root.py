from pathlib import Path
from collections import defaultdict
import pandas as pd
import pydicom

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg")
audit = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"

metadata = pd.read_csv(
    audit / "hcc_ct_series_candidates.csv", low_memory=False
)
links = pd.read_csv(
    audit / "hcc_seg_to_local_ct_uid_check.csv", low_memory=False
)

# All CT series UIDs listed in the dataset metadata.
metadata_uids = set(
    metadata["SeriesInstanceUID"].dropna().astype(str).str.strip()
)

# Series referenced by each SEG object.
seg_refs = {}
for _, row in links.iterrows():
    patient = str(row.get("PatientID", "")).strip()
    raw = str(row.get("referenced_series_uids", "")).strip()
    refs = [
        x.strip() for x in raw.split(";")
        if x.strip() and x.strip().lower() != "nan"
    ]
    seg_refs[patient] = refs

local_series = defaultdict(lambda: {
    "PatientID": "",
    "Modality": "",
    "SeriesDescription": "",
    "files": [],
})

files_scanned = 0
header_errors = 0

for path in root.rglob("*"):
    if not path.is_file() or path.name.lower().endswith(".tmp"):
        continue
    if path.suffix.lower() not in {".dcm", ""}:
        continue

    files_scanned += 1
    try:
        ds = pydicom.dcmread(
            str(path),
            stop_before_pixels=True,
            force=True,
            specific_tags=[
                "PatientID", "SeriesInstanceUID",
                "SeriesDescription", "Modality"
            ],
        )
        uid = str(getattr(ds, "SeriesInstanceUID", "")).strip()
        modality = str(getattr(ds, "Modality", "")).strip().upper()

        if not uid or modality not in {"CT", "SEG"}:
            continue

        entry = local_series[uid]
        entry["PatientID"] = str(
            getattr(ds, "PatientID", "")
        ).strip()
        entry["Modality"] = modality
        entry["SeriesDescription"] = str(
            getattr(ds, "SeriesDescription", "")
        ).strip()
        entry["files"].append(str(path))

    except Exception:
        header_errors += 1

ct_index = {
    uid: item for uid, item in local_series.items()
    if item["Modality"] == "CT"
}
local_ct_uids = set(ct_index)

print("=== WHOLE-DATASET SCAN ===")
print("Root scanned:", root)
print("Candidate files inspected:", files_scanned)
print("Local CT series:", len(ct_index))
print("Header errors:", header_errors)
print("Metadata CT UIDs found anywhere locally:",
      len(metadata_uids & local_ct_uids))
print("Metadata CT UIDs not found anywhere locally:",
      len(metadata_uids - local_ct_uids))

# Check each SEG-referenced UID against the whole dataset root.
rows = []
for patient, refs in sorted(seg_refs.items()):
    matched = [uid for uid in refs if uid in ct_index]

    if not refs:
        status = "NO_REFERENCED_SERIES_UID"
    elif not matched:
        status = "REFERENCED_CT_NOT_FOUND_ANYWHERE"
    elif any(ct_index[uid]["PatientID"] != patient for uid in matched):
        status = "PATIENT_ID_MISMATCH"
    else:
        status = "REFERENCED_CT_FOUND_ANYWHERE"

    rows.append({
        "PatientID": patient,
        "link_status": status,
        "matched_CT_UIDs": ";".join(matched),
        "matched_CT_descriptions": ";".join(
            ct_index[uid]["SeriesDescription"] for uid in matched
        ),
        "matched_CT_file_counts": ";".join(
            str(len(ct_index[uid]["files"])) for uid in matched
        ),
        "sample_local_paths": " ; ".join(
            ct_index[uid]["files"][0] for uid in matched
        ),
    })

report = pd.DataFrame(rows)
report.to_csv(audit / "hcc_seg_to_ct_whole_root_check.csv", index=False)

inventory = pd.DataFrame([
    {
        "PatientID": item["PatientID"],
        "SeriesInstanceUID": uid,
        "SeriesDescription": item["SeriesDescription"],
        "file_count": len(item["files"]),
        "sample_path": item["files"][0],
    }
    for uid, item in ct_index.items()
])
inventory.to_csv(audit / "hcc_whole_root_ct_inventory.csv", index=False)

print("\n=== SEG LINKAGE RESULTS ===")
print(report["link_status"].value_counts().to_string())

print("\n=== CASES STILL NOT LINKED ===")
print(report[report["link_status"] != "REFERENCED_CT_FOUND_ANYWHERE"][
    ["PatientID", "link_status"]
].to_string(index=False))

print("\n=== SAMPLE RECOVERED CT PATHS ===")
print(report[report["link_status"] == "REFERENCED_CT_FOUND_ANYWHERE"][
    ["PatientID", "matched_CT_descriptions", "matched_CT_file_counts",
     "sample_local_paths"]
].head(10).to_string(index=False))

print("\nReports saved:")
print(audit / "hcc_seg_to_ct_whole_root_check.csv")
print(audit / "hcc_whole_root_ct_inventory.csv")
