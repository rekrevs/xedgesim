#!/usr/bin/env python3
"""
create_test_model.py - Generate simple ONNX model for testing

Creates a simple binary anomaly detector:
- Input: 32-dimensional feature vector
- Output: Single probability score (0-1)

This is a minimal model for testing the ML inference framework.
For real research, use actual trained models.
"""

import sys

try:
    import torch
    import torch.nn as nn
    import torch.onnx
except ImportError:
    print("Error: PyTorch not installed. Install with: pip install torch")
    sys.exit(1)


class SimpleAnomalyDetector(nn.Module):
    """Simple 2-layer neural network for binary anomaly detection."""

    def __init__(self, input_dim=32, hidden_dim=16):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        x = self.sigmoid(x)
        return x


def create_onnx_model(output_path="models/anomaly_detector.onnx", input_dim=32):
    """
    Create and export ONNX model.

    Args:
        output_path: Path to save ONNX model
        input_dim: Input feature dimension
    """
    print(f"Creating ONNX model...")
    print(f"  Input dimension: {input_dim}")
    print(f"  Hidden dimension: 16")
    print(f"  Output: Single probability (0-1)")

    # Create model
    model = SimpleAnomalyDetector(input_dim=input_dim)
    model.eval()

    # Create dummy input for export
    dummy_input = torch.randn(1, input_dim)

    # Export to ONNX
    print(f"\nExporting to ONNX: {output_path}")
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        input_names=['features'],
        output_names=['probability'],
        dynamic_axes={
            'features': {0: 'batch_size'},
            'probability': {0: 'batch_size'}
        },
        opset_version=9  # Compatible with ONNX Runtime 1.16.0
    )

    print(f"✓ ONNX model saved to {output_path}")

    # Test the model with ONNX Runtime
    try:
        import onnxruntime as ort
        import numpy as np

        print("\nValidating ONNX model...")
        session = ort.InferenceSession(output_path)

        # Get input/output names
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name

        print(f"  Input: {input_name}, shape: {session.get_inputs()[0].shape}")
        print(f"  Output: {output_name}, shape: {session.get_outputs()[0].shape}")

        # Test inference
        test_input = np.random.randn(1, input_dim).astype(np.float32)
        result = session.run([output_name], {input_name: test_input})

        print(f"  Test inference: {result[0][0][0]:.4f}")
        print("✓ ONNX model validation successful")

    except ImportError:
        print("\nWarning: onnxruntime not installed, skipping validation")
        print("Install with: pip install onnxruntime")


def create_pytorch_model(output_path="models/anomaly_detector.pt", input_dim=32):
    """
    Create and save PyTorch model.

    Args:
        output_path: Path to save PyTorch model
        input_dim: Input feature dimension
    """
    print(f"\nCreating PyTorch model...")
    print(f"  Input dimension: {input_dim}")
    print(f"  Hidden dimension: 16")
    print(f"  Output: Single probability (0-1)")

    # Create model
    model = SimpleAnomalyDetector(input_dim=input_dim)
    model.eval()

    # Save PyTorch model
    print(f"\nSaving PyTorch model: {output_path}")
    torch.save(model, output_path)

    print(f"✓ PyTorch model saved to {output_path}")

    # Test the model with PyTorch
    print("\nValidating PyTorch model...")

    # Load model
    loaded_model = torch.load(output_path)
    loaded_model.eval()

    # Test inference
    test_input = torch.randn(1, input_dim)
    with torch.no_grad():
        result = loaded_model(test_input)

    print(f"  Test inference: {result.item():.4f}")
    print("✓ PyTorch model validation successful")


if __name__ == "__main__":
    import os

    # Ensure models directory exists
    os.makedirs("models", exist_ok=True)

    print("=" * 60)
    print("Creating Test Models for ML Inference Framework")
    print("=" * 60)

    # Create ONNX model (for M3a edge tier)
    create_onnx_model()

    # Create PyTorch model (for M3b cloud tier)
    create_pytorch_model()

    print("\n" + "=" * 60)
    print("✓ Both models ready for ML inference testing!")
    print("  - Edge tier (ONNX):  models/anomaly_detector.onnx")
    print("  - Cloud tier (PyTorch): models/anomaly_detector.pt")
    print("=" * 60)
