from pathlib import Path
import re
import csv
import json
import traceback

import nibabel as nib
import numpy as np
import pandas as pd

ROOT = Path(r"D:\FINAL_PROJECT")
DATASETS = ROOT / "DATASETS"
CTORG_ROOT = DATASETS / "CT-ORG"
HCC_ROOT = DATASETS / "HCC-TACE-Seg"

OUT = Path(__file__).resolve().parents[1] / "results" / "dataset_audit"
OUT.mkdir(parents=True, exist_ok=True)


def case_id(path, prefix):
    match = re.fullmatch(
        rf"{re.escape(prefix)}-(\d+)\.nii(?:\.gz)?",
        path.name,
        flags=re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def collect_nifti(root, prefix):
    found = {}
    duplicates = []

    if not root.exists():
        return found, duplicates

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        cid = case_id(path, prefix)
        if cid is None:
            continue

        if cid in found:
            duplicates.append({
                "case_id": cid,
                "first_path": str(found[cid]),
                "duplicate_path": str(path),
            })
        else:
            found[cid] = path

    return found, duplicates


def inspect_nifti(path, kind):
    row = {
        "kind": kind,
        "path": str(path),
        "file_size_bytes": path.stat().st_size,
        "status": "OK",
        "shape": "",
        "spacing_mm": "",
        "orientation": "",
        "dtype": "",
        "min_value": "",
        "max_value": "",
        "unique_labels": "",
        "error": "",
    }

    try:
        image = nib.load(str(path))
        row["shape"] = "x".join(map(str, image.shape))
        row["spacing_mm"] = "x".join(
            f"{abs(float(x)):.5g}" for x in image.header.get_zooms()[:3]
        )
        row["orientation"] = "".join(nib.aff2axcodes(image.affine))
        row["dtype"] = str(image.get_data_dtype())

        if kind == "label":
            data = np.asanyarray(image.dataobj)
            values, counts = np.unique(data, return_counts=True)
            row["unique_labels"] = json.dumps({
                str(v.item() if hasattr(v, "item") else v): int(c)
                for v, c in zip(values, counts)
            })
            row["min_value"] = float(np.min(data))
            row["max_value"] = float(np.max(data))
        else:
            # Read a small sample only; avoid loading the whole CT into RAM.
            proxy = image.dataobj
            sample = np.asanyarray(proxy[::max(1, image.shape[0] // 16),
                                         ::max(1, image.shape[1] // 16),
                                         ::max(1, image.shape[2] // 16)])
            row["min_value"] = float(np.min(sample))
            row["max_value"] = float(np.max(sample))

    except Exception as exc:
        row["status"] = "ERROR"
        row["error"] = f"{type(exc).__name__}: {exc}"

    return row


def main():
    print("=== PROJECT DATASET AUDIT ===")
    print(f"Project root: {ROOT}")
    print(f"CT-ORG root:  {CTORG_ROOT}")
    print(f"HCC root:     {HCC_ROOT}")
    print(f"Output:       {OUT}")

    volumes, duplicate_volumes = collect_nifti(CTORG_ROOT, "volume")
    labels, duplicate_labels = collect_nifti(CTORG_ROOT, "labels")

    volume_ids = set(volumes)
    label_ids = set(labels)
    matched_ids = sorted(volume_ids & label_ids)
    missing_labels = sorted(volume_ids - label_ids)
    missing_volumes = sorted(label_ids - volume_ids)

    print("\n=== CT-ORG FILE MATCHING ===")
    print(f"Volumes found:          {len(volumes)}")
    print(f"Label files found:      {len(labels)}")
    print(f"Matched case IDs:       {len(matched_ids)}")
    print(f"Volumes without labels: {len(missing_labels)}")
    print(f"Labels without volumes: {len(missing_volumes)}")
    print(f"Duplicate volume IDs:   {len(duplicate_volumes)}")
    print(f"Duplicate label IDs:    {len(duplicate_labels)}")

    pairs = []
    for cid in sorted(volume_ids | label_ids):
        volume = volumes.get(cid)
        label = labels.get(cid)
        row = {
            "case_id": cid,
            "volume_path": str(volume) if volume else "",
            "label_path": str(label) if label else "",
            "match_status": (
                "MATCHED" if volume and label
                else "MISSING_LABEL" if volume
                else "MISSING_VOLUME"
            ),
            "volume_shape": "",
            "label_shape": "",
            "shape_match": "",
            "volume_spacing_mm": "",
            "label_spacing_mm": "",
            "spacing_match": "",
        }

        if volume:
            vimg = nib.load(str(volume))
            row["volume_shape"] = "x".join(map(str, vimg.shape))
            row["volume_spacing_mm"] = "x".join(
                f"{abs(float(x)):.5g}" for x in vimg.header.get_zooms()[:3]
            )

        if label:
            limg = nib.load(str(label))
            row["label_shape"] = "x".join(map(str, limg.shape))
            row["label_spacing_mm"] = "x".join(
                f"{abs(float(x)):.5g}" for x in limg.header.get_zooms()[:3]
            )

        if volume and label:
            vimg = nib.load(str(volume))
            limg = nib.load(str(label))
            row["shape_match"] = vimg.shape == limg.shape
            row["spacing_match"] = np.allclose(
                vimg.header.get_zooms()[:3],
                limg.header.get_zooms()[:3],
                rtol=0,
                atol=1e-4,
            )

        pairs.append(row)

    pd.DataFrame(pairs).to_csv(OUT / "ctorg_pairs.csv", index=False)

    duplicates = (
        [{"kind": "volume", **x} for x in duplicate_volumes]
        + [{"kind": "label", **x} for x in duplicate_labels]
    )
    pd.DataFrame(duplicates, columns=[
        "kind", "case_id", "first_path", "duplicate_path"
    ]).to_csv(OUT / "ctorg_duplicates.csv", index=False)

    print("\n=== INSPECT NIFTI HEADERS AND LABELS ===")
    details = []
    for cid in sorted(volume_ids):
        details.append(inspect_nifti(volumes[cid], "volume"))
    for cid in sorted(label_ids):
        details.append(inspect_nifti(labels[cid], "label"))

    pd.DataFrame(details).to_csv(OUT / "ctorg_nifti_details.csv", index=False)

    print(f"NIfTI detail rows: {len(details)}")
    print("NIfTI detail report: ctorg_nifti_details.csv")

    hcc_counts = {}
    if HCC_ROOT.exists():
        for path in HCC_ROOT.rglob("*"):
            if path.is_file():
                suffix = "".join(path.suffixes).lower()
                key = suffix if suffix else "[no extension]"
                hcc_counts[key] = hcc_counts.get(key, 0) + 1

    pd.DataFrame(
        [{"extension": k, "count": v}
         for k, v in sorted(hcc_counts.items(),
                            key=lambda item: item[1], reverse=True)]
    ).to_csv(OUT / "hcc_file_inventory.csv", index=False)

    print("\n=== HCC-TACE-SEG FILE INVENTORY ===")
    for extension, count in sorted(
        hcc_counts.items(), key=lambda item: item[1], reverse=True
    ):
        print(f"{extension}: {count}")

    summary = {
        "ctorg_root_exists": CTORG_ROOT.exists(),
        "hcc_root_exists": HCC_ROOT.exists(),
        "ctorg_volumes": len(volumes),
        "ctorg_labels": len(labels),
        "ctorg_matched_cases": len(matched_ids),
        "ctorg_missing_labels": missing_labels,
        "ctorg_missing_volumes": missing_volumes,
        "ctorg_duplicate_volume_ids": len(duplicate_volumes),
        "ctorg_duplicate_label_ids": len(duplicate_labels),
        "hcc_file_counts_by_extension": hcc_counts,
        "note": (
            "Shape/spacing matches are necessary checks, not proof of "
            "full spatial alignment. Review affine matrices and image "
            "overlays before training."
        ),
    }

    with (OUT / "audit_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n=== AUDIT COMPLETE ===")
    print(f"Reports saved to: {OUT}")
    print("Review ctorg_pairs.csv and ctorg_nifti_details.csv next.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
