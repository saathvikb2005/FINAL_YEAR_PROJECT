"""Factory functions for the three experimental target models."""
from __future__ import annotations

from .unet3d import UNet3D, transfer_encoder_weights


def make_model_1_scratch(base_channels: int = 8) -> UNet3D:
    """Model 1: target tumor model initialized from scratch."""
    return UNet3D(in_channels=1, num_classes=2, base_channels=base_channels)


def make_model_2_liver_pretrained(
    liver_pretraining_checkpoint: str,
    base_channels: int = 8,
    map_location: str = "cpu",
) -> UNet3D:
    """Model 2: load CT-ORG liver-pretraining encoder into the tumor model."""
    source = UNet3D(in_channels=1, num_classes=2, base_channels=base_channels)
    checkpoint = __import__("torch").load(liver_pretraining_checkpoint, map_location=map_location)
    source.load_state_dict(checkpoint.get("model_state_dict", checkpoint), strict=True)
    target = UNet3D(in_channels=1, num_classes=2, base_channels=base_channels)
    transfer_encoder_weights(source, target)
    return target


def make_model_3_multi_organ_pretrained(
    multi_organ_pretraining_checkpoint: str,
    base_channels: int = 8,
    map_location: str = "cpu",
) -> UNet3D:
    """Model 3: load CT-ORG multi-organ-pretraining encoder into the tumor model."""
    source = UNet3D(in_channels=1, num_classes=7, base_channels=base_channels)
    checkpoint = __import__("torch").load(multi_organ_pretraining_checkpoint, map_location=map_location)
    source.load_state_dict(checkpoint.get("model_state_dict", checkpoint), strict=True)
    target = UNet3D(in_channels=1, num_classes=2, base_channels=base_channels)
    transfer_encoder_weights(source, target)
    return target
