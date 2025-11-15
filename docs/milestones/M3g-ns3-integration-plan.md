# M3g: ns-3 Integration Plan

**Milestone:** M3g - Packet-Level Network Simulation with ns-3
**Duration:** 3-4 weeks
**Effort:** ~800-1000 LOC
**Status:** PLANNED

---

## 1. Objective

Integrate ns-3 (discrete-event network simulator) to enable:
- Packet-level wireless protocol simulation (WiFi, Zigbee, LoRa)
- Realistic PHY/MAC layer behavior
- Accurate latency, jitter, and packet loss modeling
- Protocol validation and debugging

**Why this matters:** Completes Tier 1 network simulation, replaces abstract latency model with realistic protocol behavior, enables cross-layer optimization research.

---

## 2. Architecture Overview

### 2.1 Current State (Latency Model)

```
┌────────────────────────────────────┐
│ Coordinator                        │
│  ┌──────────────────────────────┐  │
│  │ LatencyNetworkModel          │  │
│  │  - Base latency + jitter     │  │
│  │  - Packet loss probability   │  │
│  │  - Simple delay calculation  │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

### 2.2 Target State (ns-3 Integration)

```
┌─────────────────────────────────────────────────────────────┐
│ Coordinator (coordinator.py)                                │
│  - Conservative synchronous lockstep                        │
│  - Routes events to/from ns-3                               │
└─────────────┬───────────────────────────────────────────────┘
              │ socket (JSON/binary protocol)
    ┌─────────▼──────────────────────────────────────────────┐
    │ ns-3 Process (C++ simulation)                          │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
    │  │ WiFi PHY/   │  │ Zigbee      │  │ LoRa PHY/   │   │
    │  │ MAC         │  │ (802.15.4)  │  │ MAC         │   │
    │  └─────────────┘  └─────────────┘  └─────────────┘   │
    │  ┌─────────────────────────────────────────────────┐  │
    │  │ TAP/TUN Bridge (to Renode/Docker)               │  │
    │  └─────────────────────────────────────────────────┘  │
    │  ┌─────────────────────────────────────────────────┐  │
    │  │ Custom xEdgeSim Module (socket interface)       │  │
    │  └─────────────────────────────────────────────────┘  │
    └────────────────────────────────────────────────────────┘
              ▲                              ▲
              │                              │
              │ TAP/TUN                      │ TAP/TUN
    ┌─────────┴────────┐         ┌──────────┴─────────┐
    │ Renode (devices) │         │ Docker (edge)      │
    └──────────────────┘         └────────────────────┘
```

---

## 3. Technical Components

### 3.1 ns-3 Custom Module (`ns3-xedgesim/`)

**Directory Structure:**
```
ns3-xedgesim/
├── model/
│   ├── xedgesim-coordinator-interface.h
│   ├── xedgesim-coordinator-interface.cc
│   ├── xedgesim-node.h
│   ├── xedgesim-node.cc
│   └── xedgesim-socket-protocol.h
├── helper/
│   ├── xedgesim-helper.h
│   └── xedgesim-helper.cc
├── examples/
│   └── xedgesim-simple-scenario.cc
└── wscript (build configuration)
```

**Core Interface (`model/xedgesim-coordinator-interface.h`):**

```cpp
#ifndef XEDGESIM_COORDINATOR_INTERFACE_H
#define XEDGESIM_COORDINATOR_INTERFACE_H

#include "ns3/socket.h"
#include "ns3/simulator.h"
#include <string>
#include <queue>

namespace ns3 {

/**
 * @brief Interface between ns-3 and xEdgeSim coordinator
 *
 * Implements the socket-based protocol for time synchronization
 * and event exchange with the coordinator.
 */
class XEdgeSimCoordinatorInterface : public Object
{
public:
  static TypeId GetTypeId();

  XEdgeSimCoordinatorInterface();
  virtual ~XEdgeSimCoordinatorInterface();

  /**
   * @brief Initialize connection to coordinator
   * @param address Coordinator socket address
   * @param port Coordinator port
   */
  void Initialize(std::string address, uint16_t port);

  /**
   * @brief Advance ns-3 simulation to target time
   * @param targetTimeUs Target time in microseconds
   * @return Events generated during advancement
   */
  std::vector<SimEvent> AdvanceTo(uint64_t targetTimeUs);

  /**
   * @brief Send packet from external node (Renode/Docker) to ns-3
   * @param srcNodeId Source node ID
   * @param dstNodeId Destination node ID
   * @param packet Packet data
   */
  void InjectPacket(std::string srcNodeId, std::string dstNodeId, Ptr<Packet> packet);

  /**
   * @brief Register callback for packet delivery
   */
  void SetPacketDeliveryCallback(Callback<void, std::string, std::string, Ptr<Packet>> callback);

private:
  void HandleCoordinatorMessage(Ptr<Socket> socket);
  void SendEvent(const SimEvent& event);

  Ptr<Socket> m_coordinatorSocket;
  uint64_t m_currentTimeUs;
  std::queue<SimEvent> m_eventQueue;
  Callback<void, std::string, std::string, Ptr<Packet>> m_deliveryCallback;
};

/**
 * @brief Simulation event structure
 */
struct SimEvent {
  std::string type;           // "PACKET_TX", "PACKET_RX", "PACKET_DROP"
  uint64_t timeUs;
  std::string srcNodeId;
  std::string dstNodeId;
  std::vector<uint8_t> data;
  uint32_t sizeBytes;
};

} // namespace ns3

#endif // XEDGESIM_COORDINATOR_INTERFACE_H
```

**Implementation (`model/xedgesim-coordinator-interface.cc`):**

```cpp
#include "xedgesim-coordinator-interface.h"
#include "ns3/log.h"
#include "ns3/inet-socket-address.h"
#include "ns3/tcp-socket-factory.h"
#include <nlohmann/json.hpp>

namespace ns3 {

NS_LOG_COMPONENT_DEFINE("XEdgeSimCoordinatorInterface");
NS_OBJECT_ENSURE_REGISTERED(XEdgeSimCoordinatorInterface);

TypeId
XEdgeSimCoordinatorInterface::GetTypeId()
{
  static TypeId tid = TypeId("ns3::XEdgeSimCoordinatorInterface")
    .SetParent<Object>()
    .SetGroupName("XEdgeSim");
  return tid;
}

XEdgeSimCoordinatorInterface::XEdgeSimCoordinatorInterface()
  : m_currentTimeUs(0)
{
  NS_LOG_FUNCTION(this);
}

XEdgeSimCoordinatorInterface::~XEdgeSimCoordinatorInterface()
{
  NS_LOG_FUNCTION(this);
}

void
XEdgeSimCoordinatorInterface::Initialize(std::string address, uint16_t port)
{
  NS_LOG_FUNCTION(this << address << port);

  // Create TCP socket to coordinator
  m_coordinatorSocket = Socket::CreateSocket(
    GetObject<Node>(), TcpSocketFactory::GetTypeId());

  InetSocketAddress coordinatorAddress(
    Ipv4Address(address.c_str()), port);

  m_coordinatorSocket->Connect(coordinatorAddress);
  m_coordinatorSocket->SetRecvCallback(
    MakeCallback(&XEdgeSimCoordinatorInterface::HandleCoordinatorMessage, this));

  NS_LOG_INFO("Connected to coordinator at " << address << ":" << port);
}

std::vector<SimEvent>
XEdgeSimCoordinatorInterface::AdvanceTo(uint64_t targetTimeUs)
{
  NS_LOG_FUNCTION(this << targetTimeUs);

  // Run ns-3 simulator until target time
  Time targetTime = MicroSeconds(targetTimeUs);
  Simulator::Stop(targetTime);
  Simulator::Run();

  // Collect events that occurred
  std::vector<SimEvent> events;
  while (!m_eventQueue.empty()) {
    events.push_back(m_eventQueue.front());
    m_eventQueue.pop();
  }

  m_currentTimeUs = targetTimeUs;
  return events;
}

void
XEdgeSimCoordinatorInterface::InjectPacket(
  std::string srcNodeId,
  std::string dstNodeId,
  Ptr<Packet> packet)
{
  NS_LOG_FUNCTION(this << srcNodeId << dstNodeId << packet->GetSize());

  // Find source and destination nodes
  // (This assumes nodes are registered with string IDs)
  // Implementation depends on node management strategy

  // For now, emit event that packet was received
  SimEvent event;
  event.type = "PACKET_INJECTED";
  event.timeUs = m_currentTimeUs;
  event.srcNodeId = srcNodeId;
  event.dstNodeId = dstNodeId;
  event.sizeBytes = packet->GetSize();

  // Copy packet data
  uint8_t buffer[packet->GetSize()];
  packet->CopyData(buffer, packet->GetSize());
  event.data = std::vector<uint8_t>(buffer, buffer + packet->GetSize());

  m_eventQueue.push(event);
}

void
XEdgeSimCoordinatorInterface::HandleCoordinatorMessage(Ptr<Socket> socket)
{
  NS_LOG_FUNCTION(this << socket);

  // Read message from coordinator
  uint8_t buffer[4096];
  int bytesRead = socket->Recv(buffer, sizeof(buffer), 0);

  if (bytesRead > 0) {
    std::string message(reinterpret_cast<char*>(buffer), bytesRead);

    // Parse JSON message
    try {
      nlohmann::json j = nlohmann::json::parse(message);

      std::string command = j["command"];

      if (command == "INJECT_PACKET") {
        // Coordinator is sending a packet to inject into ns-3
        std::string srcNodeId = j["src"];
        std::string dstNodeId = j["dst"];
        std::vector<uint8_t> data = j["data"];

        // Create ns-3 packet
        Ptr<Packet> packet = Create<Packet>(data.data(), data.size());

        // Inject into simulation
        InjectPacket(srcNodeId, dstNodeId, packet);
      }
    } catch (const std::exception& e) {
      NS_LOG_ERROR("Failed to parse coordinator message: " << e.what());
    }
  }
}

void
XEdgeSimCoordinatorInterface::SendEvent(const SimEvent& event)
{
  NS_LOG_FUNCTION(this);

  // Convert event to JSON
  nlohmann::json j;
  j["type"] = event.type;
  j["time_us"] = event.timeUs;
  j["src"] = event.srcNodeId;
  j["dst"] = event.dstNodeId;
  j["size_bytes"] = event.sizeBytes;
  j["data"] = event.data;

  std::string message = j.dump() + "\n";

  // Send to coordinator
  m_coordinatorSocket->Send(
    reinterpret_cast<const uint8_t*>(message.c_str()),
    message.size(), 0);
}

} // namespace ns3
```

### 3.2 Python Adapter (`sim/network/ns3_model.py`)

**Responsibilities:**
- Start ns-3 process with custom scenario
- Communicate via socket protocol
- Translate coordinator events to ns-3 commands
- Forward ns-3 events back to coordinator

```python
# sim/network/ns3_model.py
import subprocess
import socket
import json
import time
from typing import List, Dict
from sim.network.network_model import NetworkModel, Event

class Ns3NetworkModel(NetworkModel):
    """ns-3 packet-level network simulator integration."""

    def __init__(self, config: dict):
        super().__init__(config)

        # ns-3 configuration
        self.scenario_name = config.get('ns3_scenario', 'xedgesim-default')
        self.ns3_path = config.get('ns3_path', '/usr/local/bin/ns3')
        self.coordinator_port = config.get('coordinator_port', 5555)

        # Process and socket
        self.ns3_process = None
        self.ns3_socket = None
        self.server_socket = None

        # Topology
        self.nodes = {}  # node_id -> ns-3 node mapping
        self.channels = {}  # Wireless channels

    def start(self):
        """Start ns-3 simulation process."""
        # Create listening socket for ns-3 to connect to
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', self.coordinator_port))
        self.server_socket.listen(1)

        # Build ns-3 command
        ns3_cmd = [
            self.ns3_path, 'run',
            f'{self.scenario_name}',
            '--',
            f'--coordinatorAddress=localhost',
            f'--coordinatorPort={self.coordinator_port}'
        ]

        # Start ns-3 process
        self.ns3_process = subprocess.Popen(
            ns3_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.config.get('ns3_workspace', '.')
        )

        print(f"[Ns3NetworkModel] Started ns-3 process: {' '.join(ns3_cmd)}")

        # Wait for ns-3 to connect
        print(f"[Ns3NetworkModel] Waiting for ns-3 to connect on port {self.coordinator_port}...")
        self.ns3_socket, addr = self.server_socket.accept()
        print(f"[Ns3NetworkModel] ns-3 connected from {addr}")

        # Send initial configuration
        self._send_config()

    def _send_config(self):
        """Send topology configuration to ns-3."""
        config_msg = {
            'command': 'CONFIGURE',
            'nodes': self.config.get('nodes', []),
            'channels': self.config.get('channels', [])
        }

        self._send_message(config_msg)
        response = self._receive_message()

        if response.get('status') != 'OK':
            raise RuntimeError(f"ns-3 configuration failed: {response}")

    def _send_message(self, msg: dict):
        """Send JSON message to ns-3."""
        data = json.dumps(msg) + '\n'
        self.ns3_socket.sendall(data.encode())

    def _receive_message(self) -> dict:
        """Receive JSON message from ns-3."""
        buffer = b''
        while b'\n' not in buffer:
            chunk = self.ns3_socket.recv(4096)
            if not chunk:
                raise ConnectionError("ns-3 socket closed")
            buffer += chunk

        message = buffer.decode().strip()
        return json.loads(message)

    def advance(self, target_time_us: int) -> List[Event]:
        """Advance ns-3 simulation to target time."""
        # Send ADVANCE command
        advance_msg = {
            'command': 'ADVANCE',
            'time_us': target_time_us
        }
        self._send_message(advance_msg)

        # Receive events from ns-3
        response = self._receive_message()

        if response.get('status') != 'DONE':
            raise RuntimeError(f"ns-3 advance failed: {response}")

        # Parse events
        events = []
        for event_data in response.get('events', []):
            event = Event(
                type=event_data['type'],
                time_us=event_data['time_us'],
                src=event_data['src'],
                dst=event_data['dst'],
                payload=event_data.get('data'),
                size_bytes=event_data['size_bytes']
            )
            events.append(event)

        self.current_time_us = target_time_us
        return events

    def transmit(self, src: str, dst: str, data: bytes, size_bytes: int) -> int:
        """Inject packet from external node into ns-3."""
        # Send INJECT_PACKET command
        inject_msg = {
            'command': 'INJECT_PACKET',
            'src': src,
            'dst': dst,
            'data': list(data),  # Convert bytes to list for JSON
            'size_bytes': size_bytes
        }
        self._send_message(inject_msg)

        # ns-3 will process this during next advance()
        # Return estimated arrival time (will be refined by ns-3)
        return self.current_time_us + 1000  # Placeholder

    def stop(self):
        """Stop ns-3 simulation."""
        if self.ns3_socket:
            shutdown_msg = {'command': 'SHUTDOWN'}
            self._send_message(shutdown_msg)
            self.ns3_socket.close()

        if self.ns3_process:
            self.ns3_process.terminate()
            self.ns3_process.wait(timeout=5)

        if self.server_socket:
            self.server_socket.close()

    def __del__(self):
        self.stop()
```

### 3.3 ns-3 Scenario Script (`ns3-scenarios/xedgesim-wifi-scenario.cc`)

```cpp
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/wifi-module.h"
#include "ns3/mobility-module.h"
#include "ns3/tap-bridge-module.h"
#include "xedgesim-coordinator-interface.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("XEdgeSimWiFiScenario");

int
main(int argc, char *argv[])
{
  // Command line arguments
  std::string coordinatorAddress = "127.0.0.1";
  uint16_t coordinatorPort = 5555;
  uint32_t numDevices = 10;

  CommandLine cmd;
  cmd.AddValue("coordinatorAddress", "Coordinator socket address", coordinatorAddress);
  cmd.AddValue("coordinatorPort", "Coordinator port", coordinatorPort);
  cmd.AddValue("numDevices", "Number of device nodes", numDevices);
  cmd.Parse(argc, argv);

  // Enable logging
  LogComponentEnable("XEdgeSimCoordinatorInterface", LOG_LEVEL_INFO);

  // Create nodes
  NodeContainer deviceNodes;
  deviceNodes.Create(numDevices);

  NodeContainer gatewayNode;
  gatewayNode.Create(1);

  // Install WiFi
  WifiHelper wifi;
  wifi.SetStandard(WIFI_STANDARD_80211n);

  YansWifiPhyHelper wifiPhy;
  YansWifiChannelHelper wifiChannel = YansWifiChannelHelper::Default();
  wifiPhy.SetChannel(wifiChannel.Create());

  WifiMacHelper wifiMac;
  Ssid ssid = Ssid("xedgesim-network");

  // Configure stations (devices)
  wifiMac.SetType("ns3::StaWifiMac", "Ssid", SsidValue(ssid));
  NetDeviceContainer deviceDevices = wifi.Install(wifiPhy, wifiMac, deviceNodes);

  // Configure AP (gateway)
  wifiMac.SetType("ns3::ApWifiMac", "Ssid", SsidValue(ssid));
  NetDeviceContainer gatewayDevices = wifi.Install(wifiPhy, wifiMac, gatewayNode);

  // Mobility model (static positions for simplicity)
  MobilityHelper mobility;
  mobility.SetPositionAllocator("ns3::GridPositionAllocator",
                                 "MinX", DoubleValue(0.0),
                                 "MinY", DoubleValue(0.0),
                                 "DeltaX", DoubleValue(5.0),
                                 "DeltaY", DoubleValue(10.0),
                                 "GridWidth", UintegerValue(3),
                                 "LayoutType", StringValue("RowFirst"));
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(deviceNodes);
  mobility.Install(gatewayNode);

  // Install Internet stack
  InternetStackHelper stack;
  stack.Install(deviceNodes);
  stack.Install(gatewayNode);

  // Assign IP addresses
  Ipv4AddressHelper address;
  address.SetBase("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer deviceInterfaces = address.Assign(deviceDevices);
  Ipv4InterfaceContainer gatewayInterfaces = address.Assign(gatewayDevices);

  // TAP bridge to connect to external processes (Renode, Docker)
  TapBridgeHelper tapBridge;
  tapBridge.SetAttribute("Mode", StringValue("UseLocal"));
  tapBridge.SetAttribute("DeviceName", StringValue("xedgesim-tap0"));
  tapBridge.Install(gatewayNode.Get(0), gatewayDevices.Get(0));

  // Create coordinator interface
  Ptr<XEdgeSimCoordinatorInterface> coordinatorInterface =
    CreateObject<XEdgeSimCoordinatorInterface>();
  coordinatorInterface->Initialize(coordinatorAddress, coordinatorPort);

  // Set up packet delivery callback
  coordinatorInterface->SetPacketDeliveryCallback(
    MakeCallback([](std::string src, std::string dst, Ptr<Packet> packet) {
      NS_LOG_INFO("Packet delivered: " << src << " -> " << dst
                   << ", size=" << packet->GetSize());
    }));

  NS_LOG_INFO("xEdgeSim WiFi scenario initialized with "
               << numDevices << " devices");
  NS_LOG_INFO("Coordinator: " << coordinatorAddress << ":" << coordinatorPort);

  // Run simulation (controlled by coordinator)
  Simulator::Run();
  Simulator::Destroy();

  return 0;
}
```

### 3.4 YAML Configuration Extension

```yaml
# scenarios/vib-monitoring/ns3-scenario.yaml

simulation:
  duration_us: 60000000  # 60 seconds
  time_step_us: 1000     # 1ms steps

network:
  model: ns3
  ns3_path: /usr/local/bin/ns3
  ns3_workspace: /home/user/ns-3-dev
  scenario: xedgesim-wifi-scenario
  coordinator_port: 5555

  # ns-3 specific configuration
  ns3_config:
    protocol: wifi
    standard: 802.11n
    channel:
      propagation_loss: LogDistance
      propagation_delay: ConstantSpeed

    nodes:
      - id: device_1
        type: station
        position: [0, 0, 0]
      - id: device_2
        type: station
        position: [5, 0, 0]
      - id: gateway_1
        type: ap
        position: [10, 10, 0]

nodes:
  - type: renode
    id: device_1
    # ... Renode config
    network_interface: tap0  # Connect to ns-3 via TAP

  - type: renode
    id: device_2
    # ... Renode config
    network_interface: tap1

  - type: docker
    id: gateway_1
    # ... Docker config
    network_interface: tap2
```

---

## 4. Implementation Phases

### Phase 1: ns-3 Setup and Custom Module (Week 1)

**Objectives:**
- [ ] Install ns-3 development environment
- [ ] Create `ns3-xedgesim` custom module skeleton
- [ ] Implement basic socket interface
- [ ] Test standalone ns-3 scenario

**Deliverables:**
- ns-3 installed and working
- `ns3-xedgesim/` module compiling
- Simple test scenario running

**Testing:**
```bash
# Build ns-3 with custom module
cd ns-3-dev
./ns3 configure --enable-examples --enable-tests
./ns3 build

# Run test scenario
./ns3 run xedgesim-wifi-scenario
```

### Phase 2: Python-ns-3 Communication (Week 2)

**Objectives:**
- [ ] Implement `Ns3NetworkModel` Python class
- [ ] Establish socket communication
- [ ] Test bidirectional message exchange
- [ ] Verify time synchronization

**Deliverables:**
- `sim/network/ns3_model.py`
- Socket protocol working
- Basic integration test

**Testing:**
```python
# tests/stages/M3g/test_ns3_communication.py
def test_ns3_socket_connection():
    config = {
        'ns3_path': '/usr/local/bin/ns3',
        'ns3_scenario': 'xedgesim-wifi-scenario'
    }
    model = Ns3NetworkModel(config)
    model.start()

    # Should be connected
    assert model.ns3_socket is not None

    model.stop()

def test_ns3_time_advancement():
    model = Ns3NetworkModel(config)
    model.start()

    events = model.advance(1000000)  # 1 second

    assert model.current_time_us == 1000000
    model.stop()
```

### Phase 3: TAP/TUN Integration (Week 3)

**Objectives:**
- [ ] Set up TAP devices on host
- [ ] Configure ns-3 TapBridge
- [ ] Connect Renode network to TAP
- [ ] Test packet flow: Renode → TAP → ns-3 → TAP → Docker

**Deliverables:**
- TAP configuration scripts
- Renode TAP integration
- Docker TAP integration
- End-to-end packet test

**TAP Setup:**
```bash
# scripts/setup-tap-devices.sh
#!/bin/bash

# Create TAP devices
sudo ip tuntap add mode tap xedgesim-tap0
sudo ip tuntap add mode tap xedgesim-tap1
sudo ip tuntap add mode tap xedgesim-tap2

# Set up
sudo ip link set xedgesim-tap0 up
sudo ip link set xedgesim-tap1 up
sudo ip link set xedgesim-tap2 up

# Assign to bridge (optional)
sudo ip link add name xedgesim-br0 type bridge
sudo ip link set xedgesim-tap0 master xedgesim-br0
sudo ip link set xedgesim-tap1 master xedgesim-br0
sudo ip link set xedgesim-tap2 master xedgesim-br0
sudo ip link set xedgesim-br0 up

echo "TAP devices created and bridged"
```

### Phase 4: Protocol Support and Validation (Week 4)

**Objectives:**
- [ ] Implement WiFi scenario (802.11n)
- [ ] Implement Zigbee scenario (802.15.4)
- [ ] Add LoRa support (if needed)
- [ ] Performance benchmarking
- [ ] Determinism validation

**Deliverables:**
- Multiple protocol scenarios
- Performance benchmarks
- Determinism tests
- Documentation

**Protocol Scenarios:**

```cpp
// WiFi scenario (already shown above)

// Zigbee (802.15.4) scenario
// ns3-scenarios/xedgesim-zigbee-scenario.cc
void SetupZigbeeNetwork() {
  LrWpanHelper lrWpanHelper;

  NetDeviceContainer devices = lrWpanHelper.Install(nodes);

  lrWpanHelper.AssociateToPan(devices, 0);  // PAN ID 0

  // Set up channel
  Ptr<SingleModelSpectrumChannel> channel =
    CreateObject<SingleModelSpectrumChannel>();
  Ptr<LogDistancePropagationLossModel> propModel =
    CreateObject<LogDistancePropagationLossModel>();
  channel->AddPropagationLossModel(propModel);

  lrWpanHelper.SetChannel(channel);
}
```

---

## 5. Testing Strategy

### 5.1 Unit Tests

```python
# tests/stages/M3g/test_ns3_model.py

def test_ns3_model_initialization():
    """Test ns-3 model initializes correctly."""
    config = {
        'ns3_path': '/usr/local/bin/ns3',
        'ns3_scenario': 'xedgesim-wifi-scenario'
    }
    model = Ns3NetworkModel(config)
    assert model.scenario_name == 'xedgesim-wifi-scenario'

def test_ns3_start_stop():
    """Test ns-3 process lifecycle."""
    model = Ns3NetworkModel(config)
    model.start()

    assert model.ns3_process is not None
    assert model.ns3_process.poll() is None  # Still running

    model.stop()

    assert model.ns3_process.poll() is not None  # Terminated

def test_ns3_packet_injection():
    """Test packet injection into ns-3."""
    model = Ns3NetworkModel(config)
    model.start()

    data = b"Hello from external node"
    arrival_time = model.transmit('device_1', 'gateway_1', data, len(data))

    assert arrival_time > model.current_time_us

    model.stop()
```

### 5.2 Integration Tests

```python
# tests/stages/M3g/test_ns3_integration.py

def test_renode_ns3_packet_flow():
    """Test packet flow from Renode through ns-3 to Docker."""
    # Set up scenario
    scenario = {
        'simulation': {'duration_us': 10000000, 'time_step_us': 1000},
        'network': {'model': 'ns3', 'scenario': 'xedgesim-wifi-scenario'},
        'nodes': [
            {'type': 'renode', 'id': 'sensor_1', 'network_interface': 'tap0'},
            {'type': 'docker', 'id': 'gateway_1', 'network_interface': 'tap1'}
        ]
    }

    coordinator = Coordinator(scenario)
    coordinator.run()

    # Verify packets flowed through ns-3
    events = coordinator.get_events()
    packet_events = [e for e in events if e.type == 'PACKET_RX']

    assert len(packet_events) > 0

    # Check latency is realistic (WiFi: ~5-50ms)
    latencies = [e.latency_us for e in packet_events]
    assert 5000 < np.mean(latencies) < 50000

def test_ns3_determinism():
    """Test ns-3 simulation determinism."""
    scenario_file = 'scenarios/ns3-determinism-test.yaml'

    # Run 1
    coordinator1 = Coordinator(scenario_file)
    coordinator1.run()
    events1 = coordinator1.get_events()

    # Run 2 (same seed)
    coordinator2 = Coordinator(scenario_file)
    coordinator2.run()
    events2 = coordinator2.get_events()

    # Should be identical
    assert events1 == events2
```

### 5.3 Performance Tests

```python
# tests/stages/M3g/test_ns3_performance.py

def test_ns3_overhead():
    """Measure ns-3 simulation overhead."""
    import time

    scenario = {
        'simulation': {'duration_us': 10000000},  # 10s virtual
        'network': {'model': 'ns3'},
        'nodes': [{'type': 'renode', 'id': f'sensor_{i}'} for i in range(10)]
    }

    coordinator = Coordinator(scenario)

    wall_start = time.time()
    coordinator.run()
    wall_duration = time.time() - wall_start

    # ns-3 should be faster than real-time for simple scenarios
    assert wall_duration < 10  # < 1x slowdown

    print(f"ns-3 speedup: {10 / wall_duration:.2f}x")

def test_ns3_scalability():
    """Test ns-3 with varying node counts."""
    results = []

    for num_nodes in [10, 50, 100]:
        scenario = create_scenario(num_nodes)
        coordinator = Coordinator(scenario)

        start = time.time()
        coordinator.run()
        duration = time.time() - start

        results.append((num_nodes, duration))

    # Check scalability (should be sub-linear)
    # 10x nodes → < 10x time
    assert results[2][1] < results[0][1] * 10
```

---

## 6. Dependencies and Prerequisites

### 6.1 ns-3 Installation

```bash
# Download ns-3 (version 3.40 or later)
cd ~
git clone https://gitlab.com/nsnam/ns-3-dev.git
cd ns-3-dev

# Install dependencies (Ubuntu)
sudo apt install g++ python3 python3-dev cmake ninja-build \
  libgsl-dev libgtk-3-dev libboost-all-dev

# Configure and build
./ns3 configure --enable-examples --enable-tests
./ns3 build

# Verify installation
./ns3 run hello-simulator
```

### 6.2 Python Dependencies

```bash
pip install json5  # For JSON parsing (if needed)
```

### 6.3 TAP/TUN Utilities

```bash
sudo apt install uml-utilities bridge-utils
```

### 6.4 ns-3 Custom Module Setup

```bash
cd ~/ns-3-dev/contrib
git clone https://github.com/xedgesim/ns3-xedgesim.git
cd ..
./ns3 configure
./ns3 build
```

---

## 7. Risks and Mitigations

### Risk 1: ns-3 Build Complexity

**Risk:** ns-3 build system (waf/ns3) is complex and version-sensitive.

**Mitigation:**
- Use latest stable ns-3 (3.40+)
- Follow official build documentation
- Create Docker container with pre-built ns-3 if needed

### Risk 2: Time Synchronization Accuracy

**Risk:** ns-3 discrete-event simulation may have time quantization issues.

**Mitigation:**
- Use fine-grained time quantum (1ms or finer)
- Test synchronization accuracy early
- Add time drift monitoring

### Risk 3: TAP/TUN Configuration

**Risk:** TAP devices require root privileges and platform-specific setup.

**Mitigation:**
- Document platform-specific setup (Linux, macOS)
- Provide setup scripts
- Consider alternative: socket-based packet forwarding (no TAP)

### Risk 4: Protocol Complexity

**Risk:** WiFi/Zigbee protocol stacks have many configuration options.

**Mitigation:**
- Start with simple configurations (fixed positions, no mobility)
- Use ns-3 helpers (WifiHelper, LrWpanHelper)
- Test one protocol at a time

### Risk 5: Performance Overhead

**Risk:** ns-3 may be slower than abstract latency model.

**Mitigation:**
- Use coarser time quantum if needed
- Profile and optimize hot paths
- Consider ns-3 optimizations (parallel simulation)

---

## 8. Success Criteria

### Must Have (M3g Complete)

- [ ] ns-3 custom module compiling and working
- [ ] Python adapter communicating with ns-3 via sockets
- [ ] Time synchronization validated
- [ ] At least WiFi scenario working
- [ ] TAP/TUN integration functional
- [ ] Packet flow: Renode → ns-3 → Docker validated
- [ ] Determinism verified (same seed → same results)
- [ ] Integration tests passing

### Should Have (Stretch Goals)

- [ ] Multiple protocol support (WiFi + Zigbee)
- [ ] Performance overhead < 2x vs latency model
- [ ] LoRa support
- [ ] Mobility scenarios

### Nice to Have (Future Work)

- [ ] ns-3 visualization integration
- [ ] Parallel simulation support
- [ ] Real-time visualization of packet flow

---

## 9. Documentation Updates

### Files to Update:

1. **docs/architecture.md**
   - Update "Network Simulation" section with ns-3 implementation
   - Add ns-3 integration diagram

2. **docs/implementation-guide.md**
   - Add "ns-3 Integration" section
   - Include protocol configuration guide

3. **README.md**
   - Add ns-3 installation instructions
   - Update feature list

4. **scenarios/vib-monitoring/README.md**
   - Add ns-3 scenario examples
   - Document TAP setup

### New Documentation:

1. **docs/ns3-integration-guide.md**
   - ns-3 setup and configuration
   - Custom module development
   - Protocol scenarios
   - Troubleshooting

2. **ns3-xedgesim/README.md**
   - Module architecture
   - Building and installation
   - Example scenarios

---

## 10. Deliverables Checklist

### Code:
- [ ] `ns3-xedgesim/` - Custom ns-3 module
- [ ] `sim/network/ns3_model.py` - Python adapter
- [ ] `ns3-scenarios/` - Example scenarios (WiFi, Zigbee)
- [ ] Updated `sim/harness/coordinator.py`
- [ ] `scripts/setup-tap-devices.sh` - TAP configuration

### Tests:
- [ ] `tests/stages/M3g/test_ns3_model.py`
- [ ] `tests/stages/M3g/test_ns3_integration.py`
- [ ] `tests/stages/M3g/test_ns3_determinism.py`
- [ ] `tests/stages/M3g/test_ns3_performance.py`

### Documentation:
- [ ] M3g milestone summary
- [ ] ns-3 integration guide
- [ ] Protocol configuration guide
- [ ] TAP setup guide

### Scenarios:
- [ ] `scenarios/ns3-wifi-scenario.yaml`
- [ ] `scenarios/ns3-zigbee-scenario.yaml`

---

## 11. Timeline and Effort Estimate

| Phase | Tasks | Duration | LOC |
|-------|-------|----------|-----|
| **Phase 1** | ns-3 setup, custom module skeleton | 1 week | ~400 |
| **Phase 2** | Python adapter, socket communication | 1 week | ~300 |
| **Phase 3** | TAP/TUN integration | 1 week | ~200 |
| **Phase 4** | Protocol support, validation | 1 week | ~300 |
| **Total** | | **3-4 weeks** | **~1200** |

---

## 12. Next Steps After M3g

With both Renode (M3f) and ns-3 (M3g) integrated, the system will have:
- ✅ True device-tier emulation (Tier 1)
- ✅ Packet-level network simulation (Tier 1)
- ✅ Deployable firmware and containers
- ✅ Complete architectural vision realized

**Recommended:** Proceed to M4 (production polish) with:
- CI/CD automation
- Performance optimization
- Comprehensive documentation
- Publication preparation

---

## Notes

- **Alternative Approach:** If TAP/TUN proves too complex, can use socket-based packet forwarding as interim solution
- **Performance:** ns-3 is CPU-intensive; may need to reduce node count or use coarser time steps
- **Visualization:** ns-3 has built-in visualization tools (NetAnim) that could be integrated for debugging

---

**Status:** READY FOR IMPLEMENTATION
**Dependencies:** M3f (Renode) should be completed first for full integration testing
**Owner:** TBD
**Reviewer:** TBD
