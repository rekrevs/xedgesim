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


def create_model(output_path="models/anomaly_detector.onnx", input_dim=32):
    """
    Create and export ONNX model.

    Args:
        output_path: Path to save ONNX model
        input_dim: Input feature dimension
    """
    print(f"Creating simple anomaly detector model...")
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
        opset_version=11
    )

    print(f"✓ Model saved to {output_path}")

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
        print("✓ Model validation successful")

    except ImportError:
        print("\nWarning: onnxruntime not installed, skipping validation")
        print("Install with: pip install onnxruntime")


if __name__ == "__main__":
    import os

    # Ensure models directory exists
    os.makedirs("models", exist_ok=True)

    # Create model
    create_model()

    print("\nModel ready for ML inference testing!")
