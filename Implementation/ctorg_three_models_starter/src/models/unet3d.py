"""Small 3D U-Net for CT segmentation.

The encoder module names are intentionally identical across tasks so encoder
weights can be transferred from CT-ORG pretraining into the tumor model.
"""
from __future__ import annotations

import torch
from torch import nn


class ConvBlock3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.InstanceNorm3d(out_channels, affine=True),
            nn.LeakyReLU(0.01, inplace=True),
            nn.Conv3d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.InstanceNorm3d(out_channels, affine=True),
            nn.LeakyReLU(0.01, inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class UNet3D(nn.Module):
    """3D U-Net. `num_classes` includes background as class 0."""

    def __init__(self, in_channels: int = 1, num_classes: int = 2, base_channels: int = 8):
        super().__init__()
        c1, c2, c3, c4 = base_channels, base_channels * 2, base_channels * 4, base_channels * 8
        self.pool = nn.MaxPool3d(kernel_size=2, stride=2)

        # Encoder names must remain the same across pretraining and target models.
        self.enc1 = ConvBlock3D(in_channels, c1)
        self.enc2 = ConvBlock3D(c1, c2)
        self.enc3 = ConvBlock3D(c2, c3)
        self.enc4 = ConvBlock3D(c3, c4)
        self.bottleneck = ConvBlock3D(c4, c4 * 2)

        self.up4 = nn.ConvTranspose3d(c4 * 2, c4, kernel_size=2, stride=2)
        self.dec4 = ConvBlock3D(c4 * 2, c4)
        self.up3 = nn.ConvTranspose3d(c4, c3, kernel_size=2, stride=2)
        self.dec3 = ConvBlock3D(c3 * 2, c3)
        self.up2 = nn.ConvTranspose3d(c3, c2, kernel_size=2, stride=2)
        self.dec2 = ConvBlock3D(c2 * 2, c2)
        self.up1 = nn.ConvTranspose3d(c2, c1, kernel_size=2, stride=2)
        self.dec1 = ConvBlock3D(c1 * 2, c1)
        self.head = nn.Conv3d(c1, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Spatial dimensions should be divisible by 16.
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        b = self.bottleneck(self.pool(e4))

        d4 = self.dec4(torch.cat([self.up4(b), e4], dim=1))
        d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.head(d1)  # logits: [B, num_classes, D, H, W]


def transfer_encoder_weights(source: UNet3D, target: UNet3D) -> tuple[list[str], list[str]]:
    """Copy only encoder weights; task-specific decoder/head stay initialized for target."""
    encoder_prefixes = ("enc1.", "enc2.", "enc3.", "enc4.")
    src = source.state_dict()
    dst = target.state_dict()
    copied = []
    for key, value in src.items():
        if key.startswith(encoder_prefixes) and key in dst and dst[key].shape == value.shape:
            dst[key] = value.detach().clone()
            copied.append(key)
    target.load_state_dict(dst)
    expected = sum(1 for k in dst if k.startswith(encoder_prefixes))
    if len(copied) != expected:
        raise RuntimeError(f"Encoder transfer incomplete: copied {len(copied)} of {expected} tensors")
    return copied, []
