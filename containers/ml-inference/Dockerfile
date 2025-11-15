FROM python:3.9-slim

# Install dependencies
RUN pip install --no-cache-dir \
    onnxruntime==1.16.0 \
    paho-mqtt>=1.6.1 \
    numpy>=1.24.0

# Create app directory
WORKDIR /app

# Copy inference service
COPY inference_service.py /app/

# Create models directory (will be mounted as volume)
RUN mkdir -p /app/models

# Environment variables (can be overridden)
ENV MODEL_PATH=/app/models/anomaly_detector.onnx
ENV MQTT_BROKER_HOST=localhost
ENV MQTT_BROKER_PORT=1883

# Run inference service
CMD ["python", "-u", "inference_service.py"]
