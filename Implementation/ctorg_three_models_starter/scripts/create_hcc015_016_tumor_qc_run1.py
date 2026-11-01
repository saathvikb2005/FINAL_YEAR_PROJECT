from pathlib import Path
import csv
import numpy as np
import pydicom
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc015_016_tumor_qc_overlays_run1")
AUDIT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc_patient_consolidated_review.csv")
PATIENTS = ("HCC_015", "HCC_016")
TUMOR_SEGMENT = 2

if OUT.exists():
    raise FileExistsError(f"Refusing to overwrite existing output: {OUT}")
OUT.mkdir(parents=True)

def read_source_uids(frame):
    uids = set()
    for deriv in getattr(frame, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = getattr(src, "ReferencedSOPInstanceUID", None)
            if uid:
                uids.add(str(uid))
    return uids

def read_segment_number(frame):
    try:
        return int(frame.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    except Exception:
        return None

def hu_pixels(ds):
    pixels = ds.pixel_array.astype(np.float32)
    return pixels * float(getattr(ds, "RescaleSlope", 1)) + float(
        getattr(ds, "RescaleIntercept", 0)
    )

with AUDIT.open("r", newline="", encoding="utf-8-sig") as f:
    audit_rows = list(csv.DictReader(f))

manifest = []
errors = []

for patient in PATIENTS:
    print(f"\n========== {patient} ==========")
    patient_root = ROOT / patient
    audit_row = next((r for r in audit_rows if r.get("PatientID") == patient), None)

    if audit_row is None or not audit_row.get("SEG_path"):
        errors.append({"patient": patient, "frame": "", "error": "SEG path absent from audit"})
        print("ERROR: SEG path absent from audit.")
        continue

    seg_path = Path(audit_row["SEG_path"])
    if not seg_path.exists():
        errors.append({"patient": patient, "frame": "", "error": f"SEG file missing: {seg_path}"})
        print("ERROR: SEG file missing.")
        continue

    seg = pydicom.dcmread(str(seg_path))
    seg_pixels = seg.pixel_array
    frames = seg.PerFrameFunctionalGroupsSequence

    ct_by_uid = {}
    for path in patient_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            header = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
            if getattr(header, "Modality", "") == "CT":
                uid = str(getattr(header, "SOPInstanceUID", ""))
                if uid:
                    ct_by_uid[uid] = path
        except Exception:
            continue

    patient_out = OUT / patient
    patient_out.mkdir()

    tumor_count = 0
    for i, frame in enumerate(frames):
        segment = read_segment_number(frame)
        if segment != TUMOR_SEGMENT:
            continue

        mask = np.asarray(seg_pixels[i]) > 0
        if not mask.any():
            continue

        tumor_count += 1
        refs = read_source_uids(frame)

        record = {
            "patient_id": patient,
            "seg_frame_index_zero_based": i,
            "segment_number": segment,
            "tumor_pixels": int(mask.sum()),
            "source_reference_count": len(refs),
            "referenced_ct_sop_uid": "",
            "ct_file": "",
            "image_shape": "",
            "mask_shape": str(tuple(mask.shape)),
            "geometry_offset_mm": "",
            "overlay_path": "",
            "status": ""
        }

        if len(refs) != 1:
            record["status"] = "REVIEW_SOURCE_REFERENCE_COUNT"
            manifest.append(record)
            errors.append({
                "patient": patient, "frame": i,
                "error": f"Expected one source reference; found {len(refs)}"
            })
            continue

        uid = next(iter(refs))
        record["referenced_ct_sop_uid"] = uid
        ct_path = ct_by_uid.get(uid)

        if ct_path is None:
            record["status"] = "REVIEW_REFERENCED_CT_NOT_FOUND"
            manifest.append(record)
            errors.append({
                "patient": patient, "frame": i,
                "error": f"Referenced CT SOP UID not found locally: {uid}"
            })
            continue

        try:
            ct = pydicom.dcmread(str(ct_path))
            image = hu_pixels(ct)
            record["ct_file"] = str(ct_path)
            record["image_shape"] = str(tuple(image.shape))

            if image.shape != mask.shape:
                record["status"] = "REVIEW_DIMENSION_MISMATCH"
                manifest.append(record)
                errors.append({
                    "patient": patient, "frame": i,
                    "error": f"CT shape {image.shape} != mask shape {mask.shape}"
                })
                continue

            offset = ""
            try:
                seg_pos = np.asarray(
                    frame.PlanePositionSequence[0].ImagePositionPatient, dtype=float
                )
                ct_pos = np.asarray(ct.ImagePositionPatient, dtype=float)
                iop = np.asarray(ct.ImageOrientationPatient, dtype=float)
                normal = np.cross(iop[:3], iop[3:])
                normal /= np.linalg.norm(normal)
                offset = float(np.dot(seg_pos - ct_pos, normal))
                record["geometry_offset_mm"] = offset
            except Exception:
                pass

            out_path = patient_out / f"{patient}_frame_{i:04d}_tumor.png"
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.imshow(image, cmap="gray", vmin=-150, vmax=250)
            ax.contour(mask.astype(np.uint8), levels=[0.5], colors="red", linewidths=0.8)
            ax.set_title(
                f"{patient} | SEG frame {i} | tumor pixels {int(mask.sum())}\n"
                f"Explicit CT SOP reference | plane offset: "
                f"{offset if offset != '' else 'unavailable'} mm"
            )
            ax.axis("off")
            fig.savefig(out_path, dpi=140, bbox_inches="tight")
            plt.close(fig)

            record["overlay_path"] = str(out_path)
            record["status"] = "OVERLAY_CREATED_DIMENSIONS_MATCH"
        except Exception as exc:
            record["status"] = "REVIEW_OVERLAY_ERROR"
            errors.append({
                "patient": patient, "frame": i,
                "error": f"{type(exc).__name__}: {exc}"
            })

        manifest.append(record)

    print("SEG frames:", len(frames))
    print("Local CT SOP instances:", len(ct_by_uid))
    print("Tumor-positive frames:", tumor_count)
    print("Output directory:", patient_out)

manifest_path = OUT / "tumor_overlay_manifest.csv"
with manifest_path.open("w", newline="", encoding="utf-8") as f:
    fields = list(manifest[0].keys()) if manifest else [
        "patient_id", "seg_frame_index_zero_based", "segment_number",
        "tumor_pixels", "source_reference_count", "referenced_ct_sop_uid",
        "ct_file", "image_shape", "mask_shape", "geometry_offset_mm",
        "overlay_path", "status"
    ]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(manifest)

errors_path = OUT / "qc_errors.csv"
with errors_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["patient", "frame", "error"])
    writer.writeheader()
    writer.writerows(errors)

print("\n========== SUMMARY ==========")
print("Manifest:", manifest_path)
print("Overlay records:", len(manifest))
print("Overlays created:", sum(r["status"] == "OVERLAY_CREATED_DIMENSIONS_MATCH" for r in manifest))
print("Errors/review flags:", len(errors))
print("Error report:", errors_path)
print("No source DICOM or SEG files were modified.")
