# CT-ORG + HCC-TACE-Seg Liver-Lesion Research

## Research objective
Compare three model strategies for liver-tumor segmentation on HCC-TACE-Seg:
1. Model 1: Train from scratch.
2. Model 2: CT-ORG liver-only pretraining, followed by fine-tuning.
3. Model 3: CT-ORG multi-organ pretraining, followed by fine-tuning.

## Status as of 17 October 2026

### Completed audit milestones
- CT-ORG inventory recorded: 140 volumes/labels.
- HCC-TACE-Seg inventory recorded: 105 patient identifiers.
- Direct SEG pixel audit: 105/105 files reported DECODE_OK.
- Consolidated CT/SEG geometry and mapping review completed.
- Provisional cohort review created for all 105 patients.

### Provisional cohort decisions
| Decision | Patients |
|---|---:|
| Pending annotation QC | 88 |
| Pending mapping review | 13 |
| Excluded pending spatial validation | 1 |
| Excluded pending mapping resolution | 1 |
| Excluded pending provisional-mapping resolution | 2 |
| Total | 105 |

Successful SEG decoding does not establish spatial alignment or annotation quality. No patients are currently confirmed training-ready by the provisional cohort report.

## Key audit reports
Directory: results\dataset_audit\
- hcc_patient_consolidated_review.csv
- hcc_tumor_pixel_audit_run1.csv
- hcc_provisional_cohort_review_run1.csv
- hcc_seg_pixel_and_reference_audit.csv (retain as historical evidence)

Do not overwrite existing audit reports. Use new run-specific filenames.

## Phase 2 closure requirements
1. Complete reproducible annotation QC.
2. Resolve or formally exclude unresolved CT/SEG mappings and spatial geometry.
3. Produce a final cohort eligibility manifest with reasons and evidence.
4. Create patient-level train/validation/test splits and check for patient leakage.
5. Document label mapping, orientation, spacing, resampling, normalization, and patch extraction.
6. Run a small GPU memory pilot before training.

Special cases: HCC_003 requires spatial validation; HCC_019 requires mapping/geometry resolution; HCC_048 and HCC_089 remain provisional; HCC_104 and HCC_105 require annotation QC.

## Phase 3 plan
Use comparable preprocessing, patient-level splits, and evaluation settings for all three models. Planned metrics include Dice, HD95, precision/recall, lesion-size-stratified performance, and robustness/reliability analyses where feasible.

The recorded GPU is an NVIDIA GeForce MX570 A with 2 GB VRAM. Start with small 3D patches and conservative batch sizes.

## Environment
Virtual environment: .venv\Scripts\python.exe
Previously recorded environment: Python 3.11.9, PyTorch 2.13.0+cu132, CUDA available. Verify again before training.

## Smoke test
Run from the project directory:
 .\.venv\Scripts\python.exe scripts\test_models.py
This synthetic-input smoke test does not validate dataset alignment or annotation quality.

## Preservation rules
- Keep original datasets and source DICOM/SEG files unchanged.
- Preserve existing scripts, historical reports, and patient-specific diagnostic evidence.
- Do not mark a case training-ready solely because it reports DECODE_OK.
- Keep future manifests and audit outputs versioned and reproducible.
