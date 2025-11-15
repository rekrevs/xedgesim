#!/bin/bash
# deploy_to_edge.sh - Deploy xEdgeSim Docker containers to edge hardware
#
# Usage:
#   ./scripts/deploy_to_edge.sh \
#     --host rpi.local \
#     --user pi \
#     --image xedgesim/mosquitto:latest \
#     --config prod-mosquitto.conf
#
# This script:
#   1. Saves Docker image to tarball
#   2. Transfers image and config to edge device
#   3. Loads image on edge device
#   4. Starts container with production configuration
#   5. Validates deployment
#
# Requirements:
#   - ssh access to edge device (passwordless recommended)
#   - docker installed on edge device
#   - Sufficient disk space for container image

set -e  # Exit on error

# Default values
HOST=""
USER="pi"
IMAGE=""
CONFIG=""
CONTAINER_NAME=""
PORT="1883"
RESTART_POLICY="unless-stopped"
MEMORY_LIMIT="256m"
CPU_LIMIT="1.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --user)
            USER="$2"
            shift 2
            ;;
        --image)
            IMAGE="$2"
            shift 2
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --memory)
            MEMORY_LIMIT="$2"
            shift 2
            ;;
        --cpus)
            CPU_LIMIT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 --host HOST --user USER --image IMAGE [OPTIONS]"
            echo ""
            echo "Required:"
            echo "  --host HOST         Edge device hostname or IP"
            echo "  --user USER         SSH username (default: pi)"
            echo "  --image IMAGE       Docker image name (e.g., xedgesim/mosquitto:latest)"
            echo ""
            echo "Optional:"
            echo "  --config FILE       Production config file to copy"
            echo "  --name NAME         Container name (default: from image name)"
            echo "  --port PORT         Port to expose (default: 1883)"
            echo "  --memory LIMIT      Memory limit (default: 256m)"
            echo "  --cpus LIMIT        CPU limit (default: 1.0)"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$HOST" ]; then
    echo -e "${RED}Error: --host is required${NC}"
    exit 1
fi

if [ -z "$IMAGE" ]; then
    echo -e "${RED}Error: --image is required${NC}"
    exit 1
fi

# Extract container name from image if not specified
if [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME=$(echo "$IMAGE" | cut -d'/' -f2 | cut -d':' -f1)
fi

# Print deployment summary
echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     xEdgeSim Edge Deployment Script               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Deployment Configuration:"
echo "  Edge Device:       $USER@$HOST"
echo "  Docker Image:      $IMAGE"
echo "  Container Name:    $CONTAINER_NAME"
echo "  Port:              $PORT"
echo "  Memory Limit:      $MEMORY_LIMIT"
echo "  CPU Limit:         $CPU_LIMIT"
if [ -n "$CONFIG" ]; then
    echo "  Config File:       $CONFIG"
fi
echo ""

# Step 1: Check Docker image exists locally
echo -e "${YELLOW}[1/6]${NC} Checking Docker image locally..."
if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${IMAGE}$"; then
    echo -e "${RED}Error: Image $IMAGE not found locally${NC}"
    echo "Build the image first: docker build -t $IMAGE <build-context>"
    exit 1
fi
echo -e "${GREEN}✓${NC} Image found locally"

# Step 2: Save Docker image to tarball
echo -e "${YELLOW}[2/6]${NC} Saving Docker image to tarball..."
IMAGE_FILE="/tmp/${CONTAINER_NAME}.tar"
docker save "$IMAGE" -o "$IMAGE_FILE"
echo -e "${GREEN}✓${NC} Image saved to $IMAGE_FILE"

# Step 3: Transfer image to edge device
echo -e "${YELLOW}[3/6]${NC} Transferring image to edge device..."
scp "$IMAGE_FILE" "${USER}@${HOST}:/tmp/"
echo -e "${GREEN}✓${NC} Image transferred"

# Step 4: Transfer config if specified
if [ -n "$CONFIG" ]; then
    echo -e "${YELLOW}[4/6]${NC} Transferring production config..."
    CONFIG_DIR="/opt/${CONTAINER_NAME}/config"
    ssh "${USER}@${HOST}" "sudo mkdir -p $CONFIG_DIR"
    scp "$CONFIG" "${USER}@${HOST}:/tmp/config.tmp"
    ssh "${USER}@${HOST}" "sudo mv /tmp/config.tmp $CONFIG_DIR/$(basename $CONFIG)"
    echo -e "${GREEN}✓${NC} Config transferred"
else
    echo -e "${YELLOW}[4/6]${NC} No config specified, skipping..."
fi

# Step 5: Load image and start container on edge device
echo -e "${YELLOW}[5/6]${NC} Loading image and starting container on edge device..."

ssh "${USER}@${HOST}" << EOF
    set -e

    # Load Docker image
    echo "  Loading image..."
    docker load -i /tmp/${CONTAINER_NAME}.tar

    # Stop and remove existing container if it exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "  Stopping existing container..."
        docker stop ${CONTAINER_NAME} || true
        docker rm ${CONTAINER_NAME} || true
    fi

    # Start new container
    echo "  Starting container..."
    docker run -d \\
        --name ${CONTAINER_NAME} \\
        --restart ${RESTART_POLICY} \\
        --memory ${MEMORY_LIMIT} \\
        --cpus ${CPU_LIMIT} \\
        -p ${PORT}:${PORT} \\
        $(if [ -n "$CONFIG" ]; then echo "-v /opt/${CONTAINER_NAME}/config:/mosquitto/config -v /opt/${CONTAINER_NAME}/data:/mosquitto/data"; fi) \\
        ${IMAGE}

    # Cleanup
    rm -f /tmp/${CONTAINER_NAME}.tar

    echo "  Container started"
EOF

echo -e "${GREEN}✓${NC} Container started on edge device"

# Step 6: Validate deployment
echo -e "${YELLOW}[6/6]${NC} Validating deployment..."
sleep 2  # Give container time to start

CONTAINER_STATUS=$(ssh "${USER}@${HOST}" "docker inspect -f '{{.State.Status}}' ${CONTAINER_NAME}" 2>/dev/null || echo "not_found")

if [ "$CONTAINER_STATUS" = "running" ]; then
    echo -e "${GREEN}✓${NC} Container is running"

    # Show container logs (last 10 lines)
    echo ""
    echo "Container logs (last 10 lines):"
    echo "----------------------------------------"
    ssh "${USER}@${HOST}" "docker logs ${CONTAINER_NAME} --tail 10"
    echo "----------------------------------------"

    # Show container stats
    echo ""
    echo "Container status:"
    ssh "${USER}@${HOST}" "docker ps --filter name=${CONTAINER_NAME} --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Deployment Successful!                         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Container $CONTAINER_NAME is running on $HOST"
    echo ""
    echo "Next steps:"
    echo "  - Check logs: ssh $USER@$HOST 'docker logs $CONTAINER_NAME'"
    echo "  - Monitor: ssh $USER@$HOST 'docker stats $CONTAINER_NAME'"
    echo "  - Stop: ssh $USER@$HOST 'docker stop $CONTAINER_NAME'"
    echo ""
else
    echo -e "${RED}✗${NC} Container failed to start (status: $CONTAINER_STATUS)"
    echo ""
    echo "Container logs:"
    ssh "${USER}@${HOST}" "docker logs ${CONTAINER_NAME} 2>&1 || echo 'No logs available'"
    exit 1
fi

# Cleanup local tarball
rm -f "$IMAGE_FILE"
