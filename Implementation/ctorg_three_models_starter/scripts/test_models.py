"""Smoke-test all three model configurations without loading medical datasets."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import torch
from models.unet3d import UNet3D, transfer_encoder_weights
from models.three_models import make_model_1_scratch


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    base = 4  # very small smoke-test model; training configuration can be tuned later
    x = torch.randn(1, 1, 16, 32, 32, device=device)

    model1 = make_model_1_scratch(base_channels=base).to(device)
    with torch.no_grad():
        y1 = model1(x)
    assert tuple(y1.shape) == (1, 2, 16, 32, 32), tuple(y1.shape)

    liver_pretrain = UNet3D(num_classes=2, base_channels=base).to(device)
    multi_pretrain = UNet3D(num_classes=7, base_channels=base).to(device)
    model2 = UNet3D(num_classes=2, base_channels=base).to(device)
    model3 = UNet3D(num_classes=2, base_channels=base).to(device)
    copied2, _ = transfer_encoder_weights(liver_pretrain, model2)
    copied3, _ = transfer_encoder_weights(multi_pretrain, model3)

    with torch.no_grad():
        y2 = model2(x)
        y3 = model3(x)
    assert tuple(y2.shape) == tuple(y1.shape)
    assert tuple(y3.shape) == tuple(y1.shape)

    print(f"Device: {device}")
    print(f"Model 1 output: {tuple(y1.shape)}")
    print(f"Model 2 output: {tuple(y2.shape)}; encoder tensors copied: {len(copied2)}")
    print(f"Model 3 output: {tuple(y3.shape)}; encoder tensors copied: {len(copied3)}")
    print("PASS: architecture and encoder-transfer smoke tests completed.")


if __name__ == "__main__":
    main()
