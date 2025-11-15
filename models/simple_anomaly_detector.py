"""
Simple Anomaly Detector Model Definition

This module contains the model architecture used for testing the ML inference framework.
"""

import torch
import torch.nn as nn


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
