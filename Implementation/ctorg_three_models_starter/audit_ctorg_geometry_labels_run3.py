from pathlib import Path
import csv
import re
import time
import nibabel as nib
import numpy as np

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\CT-ORG\PKG - CT-ORG\CT-ORG\OrganSegmentations")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\ctorg_geometry_labels_audit_run3.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

def build_map(prefix):
    pattern = re.compile(rf"^{prefix}-(\d+)\.nii\.gz$", re.IGNORECASE)
    result = {}
    for p in ROOT.glob("*.nii.gz"):
        match = pattern.match(p.name)
        if match:
            result[int(match.group(1))] = p
    return result

volumes = build_map("volume")
labels = build_map("labels")
ids = sorted(set(volumes) | set(labels))
fields = [
    "ID", "VolumeFile", "LabelFile", "Status",
    "VolumeShape", "LabelShape", "VolumeSpacing_mm", "LabelSpacing_mm",
    "VolumeOrientation", "LabelOrientation", "AffineMaxAbsDifference",
    "HeaderZoomsMatch", "LabelValuesAndCounts", "ForegroundVoxelCount",
    "BackgroundVoxelCount", "NonFiniteVolumeVoxels",
    "NonFiniteLabelVoxels", "VolumeLoadError", "LabelLoadError"
]

def compact_counts(data):
    finite = np.isfinite(data)
    finite_data = data[finite]
    if finite_data.size == 0:
        return "NO_FINITE_VALUES", 0, 0, False

    rounded = np.rint(finite_data)
    integral = bool(np.all(np.abs(finite_data - rounded) <= 1e-6))
    foreground = int(np.count_nonzero(finite_data != 0))
    background = int(finite_data.size - foreground)

    if integral and np.all(rounded >= 0) and np.max(rounded) <= 100000:
        counts = np.bincount(rounded.astype(np.int64))
        pairs = [f"{i}:{int(n)}" for i, n in enumerate(counts) if n]
        label_text = ";".join(pairs)
    else:
        # Avoid an expensive unique-value scan on large arrays.
        label_text = (
            f"NON_INTEGER_OR_UNEXPECTED_RANGE;"
            f"min={float(np.min(finite_data))};max={float(np.max(finite_data))}"
        )
    return label_text, foreground, background, integral

start = time.time()
rows = []

with OUT.open("w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()

    for idx, case_id in enumerate(ids, start=1):
        row = {field: "" for field in fields}
        row["ID"] = case_id
        row["VolumeFile"] = volumes[case_id].name if case_id in volumes else ""
        row["LabelFile"] = labels[case_id].name if case_id in labels else ""
        row["Status"] = "PENDING"

        vimg = limg = None
        vdata = ldata = None

        if case_id not in volumes or case_id not in labels:
            row["Status"] = "MISSING_VOLUME_OR_LABEL"
            writer.writerow(row)
            handle.flush()
            rows.append(row)
            continue

        try:
            vimg = nib.load(str(volumes[case_id]))
            vdata = np.asanyarray(vimg.dataobj)
            row["VolumeShape"] = "x".join(map(str, vimg.shape))
            row["VolumeSpacing_mm"] = ";".join(
                f"{x:.6g}" for x in vimg.header.get_zooms()[:3]
            )
            row["VolumeOrientation"] = "".join(nib.aff2axcodes(vimg.affine))
            row["NonFiniteVolumeVoxels"] = int(
                np.count_nonzero(~np.isfinite(vdata))
            )
        except Exception as exc:
            row["VolumeLoadError"] = f"{type(exc).__name__}: {exc}"

        try:
            limg = nib.load(str(labels[case_id]))
            ldata = np.asanyarray(limg.dataobj)
            row["LabelShape"] = "x".join(map(str, limg.shape))
            row["LabelSpacing_mm"] = ";".join(
                f"{x:.6g}" for x in limg.header.get_zooms()[:3]
            )
            row["LabelOrientation"] = "".join(nib.aff2axcodes(limg.affine))
            row["NonFiniteLabelVoxels"] = int(
                np.count_nonzero(~np.isfinite(ldata))
            )
            (row["LabelValuesAndCounts"],
             row["ForegroundVoxelCount"],
             row["BackgroundVoxelCount"],
             integral_labels) = compact_counts(ldata)
        except Exception as exc:
            row["LabelLoadError"] = f"{type(exc).__name__}: {exc}"
            integral_labels = False

        if vimg is not None and limg is not None:
            same_shape = tuple(vimg.shape) == tuple(limg.shape)
            same_affine = np.allclose(
                vimg.affine, limg.affine, rtol=0, atol=1e-4
            )
            zooms_match = bool(np.allclose(
                vimg.header.get_zooms()[:3],
                limg.header.get_zooms()[:3],
                rtol=0, atol=1e-4
            ))
            row["AffineMaxAbsDifference"] = float(
                np.max(np.abs(vimg.affine - limg.affine))
            )
            row["HeaderZoomsMatch"] = zooms_match

            if (not row["VolumeLoadError"] and not row["LabelLoadError"]
                and same_shape and same_affine and zooms_match
                and row["NonFiniteVolumeVoxels"] == 0
                and row["NonFiniteLabelVoxels"] == 0
                and integral_labels):
                row["Status"] = "PASS_BASIC_GEOMETRY_AND_LABEL_CHECKS"
            else:
                row["Status"] = "REVIEW_REQUIRED"
        else:
            row["Status"] = "LOAD_ERROR"

        writer.writerow(row)
        handle.flush()
        rows.append(row)
        print(f"[{idx}/{len(ids)}] Case {case_id}: {row['Status']}", flush=True)

print("\n=== CT-ORG AUDIT SUMMARY ===")
print(f"Volume files: {len(volumes)}")
print(f"Label files: {len(labels)}")
print(f"Cases audited: {len(rows)}")
print(f"Report: {OUT}")
for status in sorted({r['Status'] for r in rows}):
    print(f"{status}: {sum(r['Status'] == status for r in rows)}")
print(f"Elapsed seconds: {time.time() - start:.1f}")
