from pathlib import Path
from collections import defaultdict
import pandas as pd
import pydicom

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
out = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit")
out.mkdir(parents=True, exist_ok=True)

# Index local CT series and CT SOP Instance UIDs.
ct_series = {}
ct_sop_to_series = {}
header_errors = []

ct_files = sorted(root.rglob("*.dcm"))
for i, path in enumerate(ct_files, start=1):
    try:
        ds = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True,
            specific_tags=[
                "Modality", "PatientID", "SeriesInstanceUID",
                "SOPInstanceUID", "SeriesDescription"
            ]
        )
        if str(getattr(ds, "Modality", "")).strip().upper() != "CT":
            continue

        series_uid = str(getattr(ds, "SeriesInstanceUID", "")).strip()
        sop_uid = str(getattr(ds, "SOPInstanceUID", "")).strip()
        patient = str(getattr(ds, "PatientID", "")).strip()

        if not series_uid:
            continue

        ct_series[series_uid] = {
            "PatientID": patient,
            "SeriesDescription": str(
                getattr(ds, "SeriesDescription", "")
            ).strip(),
        }

        if sop_uid:
            ct_sop_to_series[sop_uid] = {
                "SeriesInstanceUID": series_uid,
                "PatientID": patient,
                "path": str(path),
            }
    except Exception as exc:
        header_errors.append({"path": str(path), "error": repr(exc)})

print("Local CT series indexed:", len(ct_series))
print("Local CT SOP Instance UIDs indexed:", len(ct_sop_to_series))
print("CT header errors:", len(header_errors))

rows = []
seg_paths = []

for path in root.rglob("*.dcm"):
    try:
        ds = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True,
            specific_tags=["Modality"]
        )
        if str(getattr(ds, "Modality", "")).strip().upper() == "SEG":
            seg_paths.append(path)
    except Exception:
        pass

for path in sorted(seg_paths):
    ds = pydicom.dcmread(str(path), force=True)
    patient = str(getattr(ds, "PatientID", "")).strip()

    declared_series = set()
    referenced_sops = set()

    for item in getattr(ds, "ReferencedSeriesSequence", []):
        uid = getattr(item, "SeriesInstanceUID", None)
        if uid:
            declared_series.add(str(uid))
        for instance in getattr(item, "ReferencedInstanceSequence", []):
            sop = getattr(instance, "ReferencedSOPInstanceUID", None)
            if sop:
                referenced_sops.add(str(sop))

    for frame in getattr(ds, "PerFrameFunctionalGroupsSequence", []):
        for derivation in getattr(frame, "DerivationImageSequence", []):
            for source in getattr(derivation, "SourceImageSequence", []):
                sop = getattr(source, "ReferencedSOPInstanceUID", None)
                if sop:
                    referenced_sops.add(str(sop))

    matched_sops = [s for s in referenced_sops if s in ct_sop_to_series]
    missing_sops = [s for s in referenced_sops if s not in ct_sop_to_series]
    resolved_series = {
        ct_sop_to_series[s]["SeriesInstanceUID"] for s in matched_sops
    }
    all_series_refs = declared_series | resolved_series

    definitions = {}
    for seg in getattr(ds, "SegmentSequence", []):
        n = int(seg.SegmentNumber)
        definitions[n] = str(getattr(seg, "SegmentLabel", "UNKNOWN"))

    tumor_segments = [
        n for n, label in definitions.items()
        if any(term in label.lower() for term in ("tumor", "mass", "lesion"))
    ]

    matched_patients = {
        ct_sop_to_series[s]["PatientID"] for s in matched_sops
    }
    patient_match = (
        bool(matched_sops) and matched_patients == {patient}
    )

    if not all_series_refs and not referenced_sops:
        status = "NO_CT_REFERENCE_FOUND"
    elif not all_series_refs:
        status = "REFERENCED_CT_IMAGES_NOT_FOUND"
    elif all(uid in ct_series for uid in all_series_refs):
        status = "CT_SERIES_REFERENCE_RESOLVED"
    else:
        status = "PARTIAL_OR_UNRESOLVED_CT_REFERENCE"

    rows.append({
        "PatientID": patient,
        "SEG_path": str(path),
        "SEG_SeriesInstanceUID": str(getattr(ds, "SeriesInstanceUID", "")),
        "declared_series_references": ";".join(sorted(declared_series)),
        "referenced_CT_SOP_count": len(referenced_sops),
        "matched_local_CT_SOP_count": len(matched_sops),
        "missing_CT_SOP_count": len(missing_sops),
        "resolved_local_CT_series": ";".join(sorted(all_series_refs)),
        "link_status": status,
        "patient_match_for_resolved_SOPs": patient_match,
        "segment_definitions": repr(definitions),
        "tumor_like_segment_numbers": ";".join(map(str, tumor_segments)),
    })

report = pd.DataFrame(rows)
report_path = out / "hcc_ct_seg_linkage_new_download.csv"
report.to_csv(report_path, index=False)

print("\n=== CT-SEG LINKAGE SUMMARY ===")
print("SEG objects audited:", len(report))
print("\nLink status:")
print(report["link_status"].value_counts(dropna=False).to_string())
print("\nPatient match:")
print(report["patient_match_for_resolved_SOPs"].value_counts(dropna=False).to_string())
print("\nSEG objects with no tumor-like label:", int(
    report["tumor_like_segment_numbers"].fillna("").str.strip().eq("").sum()
))
print("\nSEG objects with missing referenced CT SOPs:", int(
    (report["missing_CT_SOP_count"] > 0).sum()
))
print("\nSample results:")
print(report[[
    "PatientID", "link_status", "referenced_CT_SOP_count",
    "matched_local_CT_SOP_count", "missing_CT_SOP_count",
    "tumor_like_segment_numbers"
]].head(15).to_string(index=False))
print("\nReport saved to:", report_path)
