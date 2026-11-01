# CT-ORG Liver-Lesion Research — Three-Model Starter

This starter defines one shared 3D U-Net architecture and three experimental initialization strategies:

1. Model 1: target model trained from scratch.
2. Model 2: encoder pretrained on CT-ORG liver segmentation, then transferred.
3. Model 3: encoder pretrained on CT-ORG multi-organ segmentation, then transferred.

## Important assumptions to verify before training

- CT-ORG pretraining labels must be mapped to the correct organ IDs.
- HCC-TACE-Seg must be converted to aligned CT volumes and tumor masks.
- The target task is binary tumor segmentation (background=0, tumor=1) in this starter.
- This implementation does not yet include data loaders, preprocessing, loss functions, training loops, or evaluation.
- Use patient-level splits and keep the test set untouched.
- The 2 GB GPU requires very small pilot patches. Do not start full training before a memory test.

## Environment

Use the project's Python 3.11 virtual environment where possible. Install PyTorch compatible with your CUDA setup. Verify first:

```powershell
python -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

The model code itself only requires PyTorch.

## Run the smoke test

From the extracted project root:

```powershell
python scripts\test_models.py
```

The test uses a tiny synthetic tensor. It does not read, modify, or require either dataset.

## Checkpoint expectations

After pretraining, save checkpoints as dictionaries containing `model_state_dict`, e.g.:

```python
torch.save({
    "model_state_dict": model.state_dict(),
    "epoch": epoch,
    "config": config,
}, output_path)
```

Model 2 expects a CT-ORG liver-pretraining checkpoint with `num_classes=2`.
Model 3 expects a CT-ORG multi-organ-pretraining checkpoint with `num_classes=7` (background + six organs).

## Next implementation step

Audit the actual CT-ORG and HCC-TACE-Seg folders and label maps. Then implement data loading and spatial-alignment checks before training.
