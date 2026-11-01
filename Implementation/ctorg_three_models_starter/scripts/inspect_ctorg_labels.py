from pathlib import Path
import nibabel as nib
import numpy as np
import pandas as pd
import json

root = Path(r"D:\FINAL_PROJECT\DATASETS\CT-ORG")
output = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"

label_files = sorted(root.rglob("labels-*.nii.gz"))
rows = []

for i, path in enumerate(label_files, start=1):
    print(f"[{i}/{len(label_files)}] {path.name}")
    image = nib.load(str(path))
    mask = np.asarray(image.dataobj)
    values, counts = np.unique(mask, return_counts=True)

    rows.append({
        "file": path.name,
        "shape": str(mask.shape),
        "spacing": str(tuple(round(float(x), 4)
                              for x in image.header.get_zooms()[:3])),
        "labels": json.dumps({
            str(v.item() if hasattr(v, "item") else v): int(c)
            for v, c in zip(values, counts)
        }),
        "unique_label_values": ",".join(str(v) for v in values),
        "background_voxels": int(counts[values == 0].sum())
            if np.any(values == 0) else 0,
        "non_background_voxels": int(mask.size - (
            counts[values == 0].sum() if np.any(values == 0) else 0
        ))
    })

    del mask

report = pd.DataFrame(rows)
report.to_csv(output / "ctorg_label_distribution.csv", index=False)

print("\n=== LABEL DISTRIBUTION SUMMARY ===")
all_values = set()
for values in report["unique_label_values"]:
    all_values.update(int(x) for x in values.split(",") if x.strip())

print("Mask files:", len(report))
print("Observed label values:", sorted(all_values))
print("Report:", output / "ctorg_label_distribution.csv")
print("\nFirst 10 masks:")
print(report[["file", "shape", "spacing",
              "unique_label_values"]].head(10).to_string(index=False))
