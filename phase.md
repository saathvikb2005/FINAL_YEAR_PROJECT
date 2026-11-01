# CT-ORG + HCC-TACE-Seg Research Project — Master Completion Checklist

We have already completed a substantial amount of dataset investigation and Phase 2 documentation. The remaining work is to convert that groundwork into a validated, reproducible three-model experiment and a publication-ready research study.

One important distinction: some tasks are complete as audits or documentation, but the underlying dataset is not yet fully approved for training. We should preserve that distinction throughout the project.

## 1. Overall project status

## Project completion tracker

In progress

Status reflects verified work and current evidence, not an estimate of total completion percentage.

Research question and three-model design

Defined

Initial dataset inventories

Completed

HCC Phase 2 investigations and reports

Completed

CT-ORG geometry and label validation

Running

Final literature review and novelty verification

Pending

Final HCC annotation QC and cohort eligibility

Pending

Frozen preprocessing and data splits

Pending

Three-model implementation and experiments

Not started / gated

Statistical analysis and paper submission

Pending

## 2. Checklist of completed work

These items are supported by the project records and command outputs available to us.

### A. Research design

- Research direction established: anatomical pretraining for liver-tumor segmentation.
- CT-ORG selected as the anatomical pretraining dataset.
- HCC-TACE-Seg selected as the target segmentation dataset.
- Three experimental arms defined.

| Model   | Training strategy                                    | Purpose                                    |
| ------- | ---------------------------------------------------- | ------------------------------------------ |
| Model 1 | Train from scratch on HCC-TACE-Seg                   | Baseline                                   |
| Model 2 | CT-ORG liver-only pretraining, then HCC fine-tuning  | Test liver-specific anatomical pretraining |
| Model 3 | CT-ORG multi-organ pretraining, then HCC fine-tuning | Test broader anatomical pretraining        |

- Initial evaluation metrics selected: Dice, HD95, precision, recall, lesion-size stratification, and robustness/reliability analysis.
- Primary research question defined: whether anatomical pretraining improves target-domain tumor segmentation compared with training from scratch, and whether multi-organ pretraining offers additional benefits.

### B. CT-ORG dataset discovery

- Dataset root located.
- Nested `OrganSegmentations` directory identified.
- Exactly 280 `.nii.gz` files found.
- 140 unique volume identifiers and 140 unique label identifiers found.
- All 140 filename pairs passed the one-to-one pairing check.
- No missing counterparts, duplicate identifiers, or unrecognized NIfTI filenames reported.

Important: pairing is verified, but geometric alignment, label correctness, and preprocessing suitability are not yet approved.

### C. HCC-TACE-Seg dataset investigation

- Dataset root and metadata path identified.
- Previous inventory recorded 105 patient identifiers.
- Initial tumor-pixel audit completed: 105/105 cases decoded, with tumor-positive pixels reported in every case.
- Source-reference and geometry investigations performed.
- Exception register created for unresolved mapping and geometry cases.
- Provisional cohort reconciliation created for all 105 patients.
- HCC_003, HCC_019, HCC_048 and HCC_089 received explicit provisional exclusion/review decisions rather than arbitrary spatial corrections.
- HCC_104 and HCC_105 overlay screening performed on 35 frames.
- Formal annotation QC remains pending for all 35 reviewed frames.
- Phase 2 closure documentation completed, with training readiness explicitly marked as not established.

### D. Documentation

- Phase 2 decision note and addendum.
- Phase 2 closure report.
- Separate investigations for source mapping, spatial provenance, and systematic/mixed geometry exceptions.
- Run-specific audit reports preserved rather than overwritten.

## 3. Remaining work — the full project roadmap

The order matters. We should not train on an uncertain cohort and try to correct the data later.

## 01

Finish CT-ORG technical validation

Current phase

- Complete the running geometry and label audit.
- Check dimensions and voxel spacing.
- Compare image and label affine matrices and orientations.
- Verify the actual set of segmentation label IDs and their counts.
- Identify empty masks, non-finite values, and unexpected label values.
- Verify intensity ranges and image data types.
- Test a small number of image–mask overlays.
- Define and validate the CT intensity windowing and normalization pipeline.
- Save a final CT-ORG validation report.

## 02

Finish HCC source mapping and annotation QC

- Reconcile the metadata, CT series references, SEG files and patient identifiers.
- Resolve or formally exclude the outstanding mapping exceptions.
- Validate image–mask spatial alignment for eligible cases.
- Review tumor-mask boundaries across representative slices.
- Record decisions, reviewer, rationale, and evidence in the QC register.
- Distinguish confirmed cases from pending and excluded cases.
- Reconcile the reported file-count discrepancy across dataset locations.
- Produce the final eligibility manifest.

Gate: no case is training-ready solely because its segmentation contains positive pixels or its geometry appears plausible.

## 03

Complete the literature review and verify novelty

- Build a literature matrix with paper, year, venue, DOI, datasets, methods and findings.
- Review CT-ORG and HCC-TACE-Seg dataset papers.
- Compare multi-dataset pretraining and transfer-learning methods.
- Review liver-tumor segmentation, small-lesion evaluation and domain robustness.
- Verify the closest competing approaches, including MultiTalent (2023), liver-metastasis transfer-learning work (2024), and newer anatomical-pretraining methods.
- Check whether the exact proposed experiment has already been reported.
- Define a narrow, evidence-supported novelty claim.
- Document research gaps and distinguish demonstrated findings from hypotheses.

## 04

Freeze preprocessing and experimental design

- Define the CT intensity window and normalization.
- Define voxel resampling and spatial alignment rules.
- Select 2D, 2.5D or 3D training inputs based on the task and hardware.
- Define patch size, sampling strategy and augmentation.
- Specify how background and organ classes are handled during pretraining.
- Freeze patient-level train/validation/test splits.
- Ensure slices from the same patient cannot leak across splits.
- Save a versioned configuration and dataset manifest.
- Define seeds, stopping criteria and checkpoint selection before training.

## 05

Validate the computing environment and run a memory pilot

- Confirm the actual PyTorch version and CUDA availability in the project environment.
- Confirm GPU memory usage and CPU fallback options.
- Select a model architecture that fits the available 2 GB GPU VRAM.
- Run a one-batch forward and backward pass.
- Verify loss calculation, gradients, checkpoint saving and reload.
- Measure peak GPU memory and runtime.
- Adjust batch size, patch size and mixed precision only after testing stability.
- Avoid unnecessary package installation until the environment is verified.

## 06

Implement and run the three models

- Implement the scratch baseline.
- Implement CT-ORG liver-only pretraining.
- Implement CT-ORG multi-organ pretraining.
- Verify all arms use comparable target-domain splits and evaluation rules.
- Save checkpoints, configurations, logs and predictions.
- Monitor overfitting and failed runs.
- Repeat experiments with planned random seeds where computationally feasible.
- Preserve failed-run logs for reproducibility.

## 07

Evaluate and analyze results

- Calculate Dice, HD95, precision and recall.
- Evaluate per patient and, where appropriate, per lesion.
- Define small-, medium- and large-lesion groups using a prespecified rule.
- Measure performance variability and robustness.
- Report uncertainty only with a defined, validated estimation method.
- Perform paired statistical comparisons with suitable confidence intervals.
- Report excluded cases and missing predictions transparently.
- Create tables, plots, qualitative overlays and error analyses.
- Perform ablation or sensitivity analyses if resources permit.

## 08

Write, verify and submit the research paper

- Finalize title, abstract and research contributions.
- Write related work using verified references.
- Document datasets, exclusions, preprocessing, splits and implementation.
- Present all model results, statistical comparisons and limitations.
- Add reproducibility details and ethical/data-use considerations.
- Verify every citation and reference.
- Compare the final claims against actual results.
- Select an appropriate venue and follow its submission format.
- Prepare supplementary material and a reproducibility package.

## 4. What must happen before training?

These are the mandatory decision gates.

| Gate | Requirement                                   | Current status                         |
| ---- | --------------------------------------------- | -------------------------------------- |
| G1   | CT-ORG image–label integrity                  | Pairing passed; geometry audit running |
| G2   | HCC source mapping and spatial validity       | Outstanding cases remain               |
| G3   | Formal tumor annotation QC                    | Pending                                |
| G4   | Final training-ready patient cohort           | Not established                        |
| G5   | Frozen preprocessing and patient-level splits | Pending                                |
| G6   | Successful memory and training pilot          | Pending                                |
| G7   | Three-arm experiments                         | Not yet authorized                     |

The existing Phase 2 closure report closes the documentation cycle, not the data-validation cycle. We should retain that distinction in all future reports.

## 5. Expected final deliverables

By the end of the project, the following should exist in the implementation and documentation folders.

- `ctorg_final_validation_report.csv`
- `hcc_final_source_mapping_manifest.csv`
- `hcc_final_annotation_qc_register.csv`
- `hcc_final_training_eligibility_manifest.csv`
- `literature_matrix_and_novelty_review.xlsx` or `.csv`
- `preprocessing_config.yaml`
- `patient_level_splits.csv`
- Reproducible scripts for all three models
- Run logs, model checkpoints and prediction outputs
- `model_comparison_results.csv`
- Statistical analysis report and figures
- Final paper draft and submission-ready files

These are target filenames, not claims that those files already exist. We will create new outputs without overwriting previous audit evidence.

## 6. How we will continue from here

Our immediate priority remains CT-ORG technical validation. The audit may take some time because it loads all 140 volumes and masks to inspect voxel data.

Once it finishes:

1. We will inspect its status counts and any exceptions.
2. We will investigate any geometry or label anomalies.
3. We will save a consolidated CT-ORG validation summary.
4. We will return to the unresolved HCC cases and finalize eligibility based on evidence.
5. In parallel, we will strengthen the literature matrix and novelty assessment.
6. Only after the data and experimental gates pass will we freeze the configuration and begin the three-model experiments.

The main objective is not merely to get three models running. It is to produce a defensible, reproducible comparison whose conclusions remain credible under research review.