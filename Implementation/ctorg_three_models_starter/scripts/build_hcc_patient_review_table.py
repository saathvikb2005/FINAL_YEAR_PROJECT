import pandas as pd
from pathlib import Path

root = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit")

link = pd.read_csv(root / "hcc_ct_seg_linkage_new_download.csv", dtype=str)
geom = pd.read_csv(root / "hcc_ct_seg_geometry_alignment.csv", dtype=str)
cohort = pd.read_csv(root / "hcc_seg_geometry_cohort_audit.csv", dtype=str)
annotation = pd.read_csv(root / "hcc_seg_annotation_audit.csv", dtype=str)

# Keep only the columns needed for the consolidated review.
geom_cols = [
    "PatientID", "geometry_status", "frames_with_source_CT_reference",
    "source_refs_found_locally", "frame_of_reference_match",
    "orientation_match", "pixel_spacing_match",
    "position_match_within_0.1mm", "max_position_delta_mm",
    "max_in_plane_delta_pixels"
]
cohort_cols = [
    "PatientID", "NumberOfFrames", "frame_positions_found",
    "declared_series_reference_count", "z_min", "z_max"
]
annotation_cols = [
    "PatientID", "status", "NumberOfFrames", "segments",
    "referenced_sop_instance_count"
]

df = link.merge(geom[geom_cols], on="PatientID", how="left", suffixes=("", "_geom"))
df = df.merge(cohort[cohort_cols], on="PatientID", how="left", suffixes=("", "_cohort"))
df = df.merge(annotation[annotation_cols], on="PatientID", how="left", suffixes=("", "_annotation"))

# Initial evidence-based categories. These are mapping-review categories,
# not clinical validation labels.
def initial_status(row):
    if row.get("link_status") == "NO_CT_REFERENCE_FOUND":
        return "UNRESOLVED_NO_DECLARED_CT_REFERENCE"
    if row.get("geometry_status") == "GEOMETRY_MATCHES_REFERENCED_CT":
        return "SOURCE_GEOMETRY_MATCH_REQUIRES_ANNOTATION_QC"
    return "REVIEW_REQUIRED"

df["mapping_review_status"] = df.apply(initial_status, axis=1)
df["manual_review_note"] = ""

# Incorporate the detailed case investigations already performed.
notes = {
    "HCC_003": (
        "Detailed source-reference geometry validation passed; "
        "annotation semantics/quality review remains pending."
    ),
    "HCC_048": (
        "Provisional CT mapping based on same-study identity and geometry; "
        "no source-image references and Frame of Reference UID mismatch. "
        "Exclude from primary validated cohort pending stronger evidence."
    ),
    "HCC_089": (
        "Candidate CT mapping visually/geometrically plausible; "
        "source references are sparse. Keep provisional pending final review."
    ),
}
for patient, note in notes.items():
    mask = df["PatientID"] == patient
    df.loc[mask, "manual_review_note"] = note
    if patient == "HCC_003":
        df.loc[mask, "mapping_review_status"] = "GEOMETRY_VALIDATED_ANNOTATION_REVIEW_PENDING"
    elif patient in ("HCC_048", "HCC_089"):
        df.loc[mask, "mapping_review_status"] = "PROVISIONAL_MAPPING_NOT_PRIMARY_COHORT"

out_path = root / "hcc_patient_consolidated_review.csv"
df.to_csv(out_path, index=False)

print("Patients in consolidated report:", len(df))
print("Unique patient IDs:", df["PatientID"].nunique())
print("Saved:", out_path)
print("\nMapping review status counts:")
print(df["mapping_review_status"].value_counts(dropna=False).to_string())
print("\nCases with manual review notes:")
print(df.loc[df["manual_review_note"] != "",
             ["PatientID", "mapping_review_status", "manual_review_note"]].to_string(index=False))
