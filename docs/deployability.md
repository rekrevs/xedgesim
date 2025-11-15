# Deployability: From Simulation to Production

**Purpose**: This document explains how Docker containers used in xEdgeSim simulation are deployment-ready and can be deployed to real edge hardware without modification.

**Audience**: Researchers and practitioners who want to validate algorithms in simulation and deploy them to production.

---

## Overview

One of xEdgeSim's key differentiators is **sim-to-prod deployability**: containers tested in simulation can be deployed directly to edge hardware (Raspberry Pi, edge servers, etc.) with minimal configuration changes.

### The Deployability Path

```
┌────────────────────────────────────────────────────────────────┐
│                   xEdgeSim Deployability Path                   │
└────────────────────────────────────────────────────────────────┘

1. DEVELOP          2. SIMULATE         3. DEPLOY          4. OPERATE
┌─────────┐        ┌─────────┐         ┌─────────┐        ┌─────────┐
│ Write   │        │ Test in │         │ Deploy  │        │ Run in  │
│ Docker  │───────>│ xEdgeSim│────────>│ to Edge │───────>│ Produc- │
│ Image   │        │ Scenario│         │ Hardware│        │ tion    │
└─────────┘        └─────────┘         └─────────┘        └─────────┘
     │                   │                   │                   │
  Define          Validate with      Same container      Monitor &
  behavior        Python nodes       + env config        optimize
```

**Key Principle**: The same Docker image used in simulation runs in production.

---

## Example: MQTT Broker Deployment

### Step 1: Build Container (Development)

Build the Mosquitto broker container:

```bash
cd containers/mqtt-broker
docker build -t xedgesim/mosquitto:latest .
```

This creates a production-ready container with:
- Eclipse Mosquitto 2.0 MQTT broker
- Development configuration (anonymous auth, logging enabled)
- Port 1883 exposed

### Step 2: Test in Simulation

Create a YAML scenario using the broker:

```yaml
# scenarios/mqtt_test.yaml
simulation:
  duration_s: 60
  seed: 42

nodes:
  - id: mqtt-broker
    type: broker
    implementation: docker
    port: 1883
    docker:
      image: xedgesim/mosquitto:latest
      build_context: containers/mqtt-broker
      ports:
        1883: 1883

  - id: sensor1
    type: sensor
    implementation: python_model
    port: 5001

  - id: gateway1
    type: gateway
    implementation: python_model
    port: 5002
```

Run simulation (when full scenario runner is implemented in M3+):

```bash
python sim/harness/run_scenario.py scenarios/mqtt_test.yaml
```

**What this validates:**
- Broker starts successfully
- Sensors can publish messages
- Gateway can subscribe and receive messages
- End-to-end MQTT flow works

### Step 3: Deploy to Edge Hardware

Deploy the same container to a Raspberry Pi:

```bash
# On Raspberry Pi (or edge server)
docker run -d \
  --name mosquitto \
  --restart unless-stopped \
  -p 1883:1883 \
  -v /opt/mosquitto/config:/mosquitto/config \
  -v /opt/mosquitto/data:/mosquitto/data \
  xedgesim/mosquitto:latest
```

**What changed:**
- Added `--restart unless-stopped` for production resilience
- Added volume mounts for persistent config and data
- Same image, same port, same behavior

### Step 4: Update Configuration for Production

Create production mosquitto.conf on edge device:

```conf
# /opt/mosquitto/config/mosquitto.conf
listener 1883 0.0.0.0

# PRODUCTION: Require authentication
allow_anonymous false
password_file /mosquitto/config/passwd

# PRODUCTION: Enable persistence
persistence true
persistence_location /mosquitto/data/

# PRODUCTION: Less verbose logging
log_dest file /mosquitto/log/mosquitto.log
log_type error
log_type warning
```

Restart broker to apply config:

```bash
docker restart mosquitto
```

---

## Simulation vs Production Configuration

### Key Differences

| Aspect | Simulation | Production |
|--------|-----------|------------|
| **Authentication** | Anonymous (allow_anonymous: true) | Required (password file) |
| **Persistence** | Disabled (testing) | Enabled (reliability) |
| **Logging** | Verbose (stdout, all types) | Minimal (file, errors only) |
| **Restart Policy** | None (controlled by simulator) | unless-stopped (resilience) |
| **Volumes** | Ephemeral (container lifecycle) | Persistent (host mounts) |
| **Networking** | Container IP or localhost | Host network or port mapping |

### Why These Differences?

**Simulation optimizes for:**
- Fast iteration (no authentication overhead)
- Debugging (verbose logging to stdout)
- Determinism (clean state each run)
- Isolation (ephemeral containers)

**Production requires:**
- Security (authentication, authorization)
- Reliability (persistence, restart policies)
- Efficiency (minimal logging)
- Integration (persistent volumes, host networking)

**The container image stays the same** - only configuration changes.

---

## Deployment Scripts

### Example: Deploy to Raspberry Pi

Use the provided deployment script:

```bash
./scripts/deploy_to_edge.sh \
  --host rpi.local \
  --user pi \
  --image xedgesim/mosquitto:latest \
  --config /opt/mosquitto/config/mosquitto.conf
```

This script:
1. Transfers container image to edge device
2. Copies production configuration
3. Starts container with production settings
4. Validates deployment (health check)

### Manual Deployment Steps

If you prefer manual deployment:

```bash
# 1. Save image to tarball (on development machine)
docker save xedgesim/mosquitto:latest -o mosquitto.tar

# 2. Transfer to edge device
scp mosquitto.tar pi@rpi.local:/tmp/

# 3. Load image on edge device
ssh pi@rpi.local "docker load -i /tmp/mosquitto.tar"

# 4. Copy production config
scp prod-mosquitto.conf pi@rpi.local:/opt/mosquitto/config/mosquitto.conf

# 5. Start container
ssh pi@rpi.local "docker run -d \
  --name mosquitto \
  --restart unless-stopped \
  -p 1883:1883 \
  -v /opt/mosquitto/config:/mosquitto/config \
  -v /opt/mosquitto/data:/mosquitto/data \
  xedgesim/mosquitto:latest"

# 6. Verify deployment
ssh pi@rpi.local "docker ps | grep mosquitto"
ssh pi@rpi.local "docker logs mosquitto --tail 50"
```

---

## Container Registry Usage

### Optional: Push to Docker Hub

For easier deployment, push images to Docker Hub:

```bash
# Tag image for Docker Hub
docker tag xedgesim/mosquitto:latest yourusername/mosquitto:latest

# Login to Docker Hub
docker login

# Push image
docker push yourusername/mosquitto:latest
```

Then deploy from registry:

```bash
# On edge device
docker pull yourusername/mosquitto:latest
docker run -d --name mosquitto ... yourusername/mosquitto:latest
```

### Private Registry

For production deployments, use a private registry:

```bash
# Tag for private registry
docker tag xedgesim/mosquitto:latest registry.example.com/mosquitto:latest

# Push to private registry
docker push registry.example.com/mosquitto:latest

# Deploy from private registry
docker pull registry.example.com/mosquitto:latest
```

---

## Testing Workflow

### Recommended Workflow

1. **Develop** container image with development configuration
2. **Simulate** using xEdgeSim YAML scenarios
   - Validate functionality with Python nodes
   - Test end-to-end message flows
   - Verify integration with other components
3. **Stage** on local edge hardware (e.g., spare Raspberry Pi)
   - Deploy with production configuration
   - Test with real sensors/gateways
   - Verify performance and resource usage
4. **Deploy** to production edge fleet
   - Use deployment script or CI/CD pipeline
   - Monitor health and metrics
   - Iterate based on production feedback

### Validation Checklist

Before deploying to production:

- [ ] Container starts successfully in simulation
- [ ] All tests pass in simulation
- [ ] Production configuration reviewed (auth, persistence, logging)
- [ ] Deployment script tested on staging hardware
- [ ] Resource usage acceptable (CPU, memory, storage)
- [ ] Backup and recovery procedure documented
- [ ] Monitoring and alerting configured

---

## Edge Hardware Considerations

### Raspberry Pi

**Tested on:** Raspberry Pi 4 Model B (4GB RAM)

**Architecture:** ARM64 (aarch64)

**Considerations:**
- Use ARM-compatible base images (eclipse-mosquitto supports arm64)
- Limit resource usage (set `--memory` and `--cpus` flags)
- Use SD card or external storage for persistent volumes
- Monitor temperature (MQTT broker is lightweight but check in summer)

**Example with resource limits:**
```bash
docker run -d \
  --name mosquitto \
  --restart unless-stopped \
  --memory 128m \
  --cpus 0.5 \
  -p 1883:1883 \
  xedgesim/mosquitto:latest
```

### Edge Servers (x86_64)

**Example:** Intel NUC, Dell Edge Gateway

**Considerations:**
- More resources available (can run multiple containers)
- Consider Docker Compose for multi-container deployments
- Use host networking for better performance
- Enable logging drivers for centralized logging

---

## Multi-Container Deployments

### Docker Compose Example

For edge servers running multiple services:

```yaml
# docker-compose.yml
version: '3.8'

services:
  mosquitto:
    image: xedgesim/mosquitto:latest
    container_name: mosquitto
    restart: unless-stopped
    ports:
      - "1883:1883"
    volumes:
      - ./config:/mosquitto/config
      - ./data:/mosquitto/data
    networks:
      - edge

  gateway:
    image: xedgesim/gateway:latest  # When implemented in M3+
    container_name: gateway
    restart: unless-stopped
    depends_on:
      - mosquitto
    environment:
      MQTT_BROKER: mosquitto:1883
    networks:
      - edge

networks:
  edge:
    driver: bridge
```

Deploy stack:
```bash
docker-compose up -d
```

---

## Troubleshooting

### Common Issues

**Issue:** Container fails to start on Raspberry Pi
- **Cause:** Wrong architecture (amd64 vs arm64)
- **Solution:** Build multi-arch image or use arm64 base

**Issue:** MQTT clients can't connect after deployment
- **Cause:** Firewall blocking port 1883
- **Solution:** Open port: `sudo ufw allow 1883`

**Issue:** Broker runs out of memory
- **Cause:** Too many retained messages or persistent sessions
- **Solution:** Set resource limits, configure message retention limits

**Issue:** Container doesn't restart after reboot
- **Cause:** Missing `--restart unless-stopped` flag
- **Solution:** Recreate container with restart policy

---

## Next Steps

### M3+: Full Deployment Automation

Future milestones will add:
- CI/CD integration (GitHub Actions → edge deployment)
- Fleet management (deploy to multiple edge devices)
- Canary deployments (gradual rollout)
- Rollback automation (revert failed deployments)
- Health monitoring and auto-healing

### Current State (M2)

M2 provides the foundation:
- ✅ Containers are deployment-ready
- ✅ Configuration differences documented
- ✅ Manual deployment workflow validated
- ✅ Example scripts provided

**The sim-to-prod path exists** - automation comes in M4.

---

## Summary

xEdgeSim's deployability model enables:

1. **Develop once**: Write Docker containers with development config
2. **Test in simulation**: Validate with xEdgeSim YAML scenarios
3. **Deploy to edge**: Use same containers with production config
4. **Iterate quickly**: Simulation accelerates development cycles

**Key Insight**: The container image is the unit of deployability. Configuration adapts to environment, but behavior is consistent.

This bridges the gap between simulation and production, enabling researchers to validate algorithms realistically before deployment.
