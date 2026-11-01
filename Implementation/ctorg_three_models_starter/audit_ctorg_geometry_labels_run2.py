from pathlib import Path
import csv
import re
import nibabel as nib
import numpy as np

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\CT-ORG\PKG - CT-ORG\CT-ORG\OrganSegmentations")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\ctorg_geometry_labels_audit_run2.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

def nii_map(prefix):
    result = {}
    pattern = re.compile(rf"^{prefix}-(\d+)\.nii\.gz$", re.IGNORECASE)
    for p in ROOT.glob("*.nii.gz"):
        m = pattern.match(p.name)
        if m:
            result[int(m.group(1))] = p
    return result

volumes = nii_map("volume")
labels = nii_map("labels")
rows = []

for case_id in sorted(set(volumes) | set(labels)):
    row = {
        "ID": case_id,
        "VolumeFile": volumes.get(case_id, Path()).name if case_id in volumes else "",
        "LabelFile": labels.get(case_id, Path()).name if case_id in labels else "",
        "Status": "PENDING",
        "VolumeShape": "",
        "LabelShape": "",
        "VolumeSpacing_mm": "",
        "LabelSpacing_mm": "",
        "VolumeOrientation": "",
        "LabelOrientation": "",
        "AffineMaxAbsDifference": "",
        "HeaderZoomsMatch": "",
        "LabelValues": "",
        "ForegroundVoxelCount": "",
        "BackgroundVoxelCount": "",
        "NonFiniteVolumeVoxels": "",
        "NonFiniteLabelVoxels": "",
        "VolumeLoadError": "",
        "LabelLoadError": "",
    }

    if case_id not in volumes or case_id not in labels:
        row["Status"] = "MISSING_VOLUME_OR_LABEL"
        rows.append(row)
        continue

    try:
        vimg = nib.load(str(volumes[case_id]))
        vdata = np.asanyarray(vimg.dataobj)
        row["VolumeShape"] = "x".join(map(str, vimg.shape))
        row["VolumeSpacing_mm"] = ";".join(f"{x:.6g}" for x in vimg.header.get_zooms()[:3])
        row["VolumeOrientation"] = "".join(nib.aff2axcodes(vimg.affine))
        row["NonFiniteVolumeVoxels"] = int(np.count_nonzero(~np.isfinite(vdata)))
        row["VolumeLoadError"] = ""
    except Exception as e:
        row["VolumeLoadError"] = f"{type(e).__name__}: {e}"
        vimg = None
        vdata = None

    try:
        limg = nib.load(str(labels[case_id]))
        ldata = np.asanyarray(limg.dataobj)
        row["LabelShape"] = "x".join(map(str, limg.shape))
        row["LabelSpacing_mm"] = ";".join(f"{x:.6g}" for x in limg.header.get_zooms()[:3])
        row["LabelOrientation"] = "".join(nib.aff2axcodes(limg.affine))
        row["NonFiniteLabelVoxels"] = int(np.count_nonzero(~np.isfinite(ldata)))
        row["LabelLoadError"] = ""

        finite = np.isfinite(ldata)
        if np.any(finite):
            vals, counts = np.unique(ldata[finite], return_counts=True)
            row["LabelValues"] = ";".join(
                f"{int(x) if float(x).is_integer() else x}:{int(n)}"
                for x, n in zip(vals, counts)
            )
            row["ForegroundVoxelCount"] = int(np.count_nonzero(finite & (ldata != 0)))
            row["BackgroundVoxelCount"] = int(np.count_nonzero(finite & (ldata == 0)))
        else:
            row["LabelValues"] = "NO_FINITE_VALUES"
    except Exception as e:
        row["LabelLoadError"] = f"{type(e).__name__}: {e}"
        limg = None
        ldata = None

    if vimg is not None and limg is not None:
        same_shape = tuple(vimg.shape) == tuple(limg.shape)
        same_affine = np.allclose(vimg.affine, limg.affine, rtol=0, atol=1e-4)
        vz = np.asarray(vimg.header.get_zooms()[:3])
        lz = np.asarray(limg.header.get_zooms()[:3])
        zooms_match = bool(np.allclose(vz, lz, rtol=0, atol=1e-4))
        row["AffineMaxAbsDifference"] = float(np.max(np.abs(vimg.affine - limg.affine)))
        row["HeaderZoomsMatch"] = zooms_match

        finite_labels = ldata[np.isfinite(ldata)]
        integral_labels = bool(
            finite_labels.size > 0 and
            np.all(np.isclose(finite_labels, np.round(finite_labels), atol=1e-6))
        )
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

    rows.append(row)

fields = list(rows[0].keys()) if rows else ["ID", "Status"]
with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print("CT-ORG geometry and label audit complete.")
print(f"Volume files: {len(volumes)}")
print(f"Label files: {len(labels)}")
print(f"Cases audited: {len(rows)}")
print(f"Report: {OUT}")
print("\nStatus counts:")
for status in sorted({r["Status"] for r in rows}):
    print(f"  {status}: {sum(r['Status'] == status for r in rows)}")
print("\nFirst 15 cases:")
for r in rows[:15]:
    print(f"  ID {r['ID']}: {r['Status']}; shape={r['VolumeShape']}; "
          f"labels={r['LabelValues'][:100]}")
