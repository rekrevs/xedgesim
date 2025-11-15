FROM python:3.9-slim

# Copy echo service script
COPY echo_service.py /app/echo_service.py

WORKDIR /app

# Expose port 5000 for socket communication
EXPOSE 5000

# Run echo service
CMD ["python", "-u", "echo_service.py"]
