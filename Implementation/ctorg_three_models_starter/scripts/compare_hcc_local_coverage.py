from pathlib import Path
import pandas as pd

audit = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"

metadata = pd.read_csv(
    audit / "hcc_ct_series_candidates.csv", low_memory=False
)
local = pd.read_csv(
    audit / "hcc_local_ct_series_inventory.csv", low_memory=False
)
links = pd.read_csv(
    audit / "hcc_seg_to_local_ct_uid_check.csv", low_memory=False
)

def clean(series):
    return series.fillna("").astype(str).str.strip()

metadata["PatientID"] = clean(metadata["PatientID"])
metadata["SeriesInstanceUID"] = clean(metadata["SeriesInstanceUID"])
local["PatientID"] = clean(local["PatientID"])
local["SeriesInstanceUID"] = clean(local["SeriesInstanceUID"])

local_uids = set(local["SeriesInstanceUID"])
local_patients = set(local["PatientID"]) - {""}
metadata_patients = set(metadata["PatientID"]) - {""}

metadata["present_locally"] = metadata["SeriesInstanceUID"].isin(local_uids)

patient_rows = []
for patient in sorted(metadata_patients | local_patients):
    m = metadata[metadata["PatientID"] == patient]
    l = local[local["PatientID"] == patient]
    patient_rows.append({
        "PatientID": patient,
        "metadata_CT_series": len(m),
        "metadata_series_found_locally": int(m["present_locally"].sum()),
        "local_CT_series": len(l),
        "local_CT_files": int(l["local_file_count"].sum()) if len(l) else 0,
        "status": (
            "NO_LOCAL_CT_SERIES" if len(l) == 0
            else "ALL_METADATA_SERIES_FOUND" if m["present_locally"].all()
            else "PARTIAL_CT_SERIES"
        ),
        "metadata_paths": " ; ".join(
            sorted(set(clean(m["S5cmdManifestPath"])) - {""})
        ) if "S5cmdManifestPath" in m.columns else ""
    })

patients = pd.DataFrame(patient_rows)
patients.to_csv(audit / "hcc_patient_local_ct_comparison.csv", index=False)

missing_series = metadata[~metadata["present_locally"]].copy()
missing_series.to_csv(audit / "hcc_metadata_ct_series_not_local.csv", index=False)

print("=== OVERALL COMPARISON ===")
print("Patients in metadata:", len(metadata_patients))
print("Patients with any local CT:", len(local_patients))
print("Metadata CT series:", len(metadata))
print("Metadata CT series found locally:", int(metadata["present_locally"].sum()))
print("Metadata CT series not found locally:", int((~metadata["present_locally"]).sum()))

print("\n=== PATIENT COVERAGE STATUS ===")
print(patients["status"].value_counts().to_string())

print("\n=== PATIENTS WITH NO LOCAL CT SERIES ===")
print(patients[patients["status"] == "NO_LOCAL_CT_SERIES"][
    ["PatientID", "metadata_CT_series", "metadata_paths"]
].to_string(index=False))

print("\n=== SAMPLE SERIES MISSING LOCALLY ===")
cols = [
    c for c in [
        "PatientID", "SeriesDescription", "SeriesInstanceUID",
        "ImageCount", "S5cmdManifestPath"
    ] if c in missing_series.columns
]
print(missing_series[cols].head(20).to_string(index=False))

print("\nReports saved:")
print(audit / "hcc_patient_local_ct_comparison.csv")
print(audit / "hcc_metadata_ct_series_not_local.csv")
