from pathlib import Path
from collections import Counter, defaultdict
import pandas as pd
import pydicom

project = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter")
audit = project / "results" / "dataset_audit"
dataset = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC")
patient_root = dataset / "hcc_tace_seg"

seg_csv = audit / "hcc_seg_pixel_and_reference_audit.csv"
seg_df = pd.read_csv(seg_csv, low_memory=False)

# Build a local index from DICOM headers.
series = defaultdict(lambda: {
    "PatientID": "",
    "SeriesInstanceUID": "",
    "SeriesDescription": "",
    "Modality": "",
    "files": [],
})
errors = 0
dicom_files = 0

for path in patient_root.rglob("*"):
    if not path.is_file():
        continue
    if path.name.lower().endswith(".tmp"):
        continue
    if path.suffix.lower() not in {".dcm", ""}:
        continue

    try:
        ds = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True,
            specific_tags=[
                "PatientID", "SeriesInstanceUID", "SeriesDescription",
                "Modality", "SOPInstanceUID"
            ]
        )
        uid = str(getattr(ds, "SeriesInstanceUID", "")).strip()
        modality = str(getattr(ds, "Modality", "")).strip().upper()
        if not uid or modality not in {"CT", "SEG"}:
            continue

        dicom_files += 1
        item = series[uid]
        item["PatientID"] = str(getattr(ds, "PatientID", "")).strip()
        item["SeriesInstanceUID"] = uid
        item["SeriesDescription"] = str(
            getattr(ds, "SeriesDescription", "")
        ).strip()
        item["Modality"] = modality
        item["files"].append(str(path))

    except Exception:
        errors += 1

ct_index = {
    uid: item for uid, item in series.items()
    if item["Modality"] == "CT"
}

print("=== LOCAL DICOM SCAN ===")
print("DICOM CT/SEG files indexed:", dicom_files)
print("CT series found:", len(ct_index))
print("Header read errors:", errors)

ct_rows = []
for uid, item in ct_index.items():
    ct_rows.append({
        "PatientID": item["PatientID"],
        "SeriesInstanceUID": uid,
        "SeriesDescription": item["SeriesDescription"],
        "local_file_count": len(item["files"]),
        "sample_local_path": item["files"][0] if item["files"] else "",
    })

ct_inventory = pd.DataFrame(ct_rows)
ct_inventory.to_csv(audit / "hcc_local_ct_series_inventory.csv", index=False)

results = []
for _, row in seg_df.iterrows():
    patient = str(row.get("PatientID", "")).strip()
    raw = str(row.get("referenced_series_uids", "")).strip()
    refs = [
        x.strip() for x in raw.split(";")
        if x.strip() and x.strip().lower() != "nan"
    ]

    matches = [ct_index[uid] for uid in refs if uid in ct_index]

    if not refs:
        status = "NO_REFERENCED_SERIES_UID"
    elif not matches:
        status = "REFERENCED_CT_UID_NOT_FOUND_LOCALLY"
    elif any(x["PatientID"] != patient for x in matches):
        status = "LOCAL_CT_PATIENT_ID_MISMATCH"
    else:
        status = "LOCAL_CT_UID_FOUND"

    results.append({
        "PatientID": patient,
        "referenced_series_uids": raw,
        "link_status": status,
        "matched_local_CT_UIDs": ";".join(
            x["SeriesInstanceUID"] for x in matches
        ),
        "matched_local_CT_descriptions": ";".join(
            x["SeriesDescription"] for x in matches
        ),
        "matched_local_CT_file_counts": ";".join(
            str(len(x["files"])) for x in matches
        ),
        "matched_local_CT_sample_paths": ";".join(
            x["files"][0] for x in matches if x["files"]
        ),
    })

report = pd.DataFrame(results)
report.to_csv(audit / "hcc_seg_to_local_ct_uid_check.csv", index=False)

print("\n=== SEG TO LOCAL CT UID CHECK ===")
print(report["link_status"].value_counts(dropna=False).to_string())

print("\n=== SAMPLE RESULTS ===")
print(report[[
    "PatientID", "link_status",
    "matched_local_CT_descriptions",
    "matched_local_CT_file_counts"
]].head(20).to_string(index=False))

print("\n=== CT SERIES COUNTS BY PATIENT ===")
if not ct_inventory.empty:
    print(
        ct_inventory.groupby("PatientID").size()
        .describe().to_string()
    )

print("\nReports saved:")
print(audit / "hcc_local_ct_series_inventory.csv")
print(audit / "hcc_seg_to_local_ct_uid_check.csv")

