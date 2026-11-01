from pathlib import Path
import pandas as pd
import numpy as np

audit_dir = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"

csv_path = audit_dir / "ctorg_label_distribution.csv"
df = pd.read_csv(csv_path)

all_labels = set()
max_deviation = 0.0
problem_values = []

for _, row in df.iterrows():
    values = [float(x) for x in
              str(row["unique_label_values"]).split(",") if x.strip()]

    for value in values:
        nearest = round(value)
        deviation = abs(value - nearest)
        max_deviation = max(max_deviation, deviation)

        if deviation > 1e-4:
            problem_values.append((row["file"], value, deviation))

        all_labels.add(int(nearest))

print("=== CT-ORG LABEL SUMMARY ===")
print("Mask files:", len(df))
print("Observed rounded label IDs:", sorted(all_labels))
print("Maximum distance from nearest integer:", max_deviation)
print("Values farther than 0.0001 from an integer:",
      len(problem_values))

if problem_values:
    print("\nFirst 20 suspicious values:")
    for item in problem_values[:20]:
        print(item)

print("\n=== MASK LABEL PATTERNS ===")
df["rounded_label_pattern"] = df["unique_label_values"].apply(
    lambda s: ",".join(
        str(int(round(float(x))))
        for x in str(s).split(",") if x.strip()
    )
)

print(df.groupby("rounded_label_pattern").size()
      .sort_values(ascending=False).to_string())

print("\nNo source files were modified.")
