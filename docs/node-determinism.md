# Deterministic Socket-Based Simulation Nodes

## Overview

This guide explains how to implement deterministic simulation nodes as **external processes** that connect to the xEdgeSim coordinator via sockets. This applies to any node implemented as a separate process in the host operating system (e.g., edge gateway models, cloud services, statistical device models).

**Target audience**: Developers implementing simulated nodes in any programming language (Python, Go, C++, Java, etc.) that participate in deterministic co-simulation.

**Key principle**: All nodes must operate in **virtual time** (not wall-clock time) to achieve deterministic, reproducible simulations.

---

## 1. The Determinism Problem

### 1.1 Wall-Clock Time vs Virtual Time

**Wall-clock time** (real time):
- System clock: `time()`, `gettimeofday()`, `clock_gettime()`
- Sleep functions: `sleep()`, `usleep()`, `nanosleep()`
- Non-deterministic: Depends on CPU scheduling, system load, I/O latency
- **Problem**: Two runs of the same simulation produce different results

**Virtual time** (simulation time):
- Managed by the coordinator
- Advances in discrete steps (e.g., 100μs, 1ms, 10ms)
- Deterministic: Same inputs → same outputs, always
- **Solution**: Nodes track virtual time, coordinator controls advancement

### 1.2 Why Process-Based Nodes Are Challenging

Unlike threads or in-process components, external processes:
- Have their own scheduler (OS decides when to run)
- Cannot share memory with coordinator
- Cannot be directly controlled by coordinator
- May use wall-clock time APIs by default

**Solution**: Event-driven architecture with explicit time synchronization over sockets.

---

## 2. Socket Protocol for Time Synchronization

### 2.1 Conservative Synchronous Lockstep Algorithm

The coordinator uses a **lockstep** algorithm to synchronize all nodes:

```
┌────────────┐         ┌──────────┐         ┌──────────┐
│ Coordinator│         │ Node A   │         │ Node B   │
└────────────┘         └──────────┘         └──────────┘
      │                      │                    │
      │  ADVANCE 1000000     │                    │
      ├─────────────────────>│                    │
      │                      │ (process events    │
      │                      │  during [0, 1ms))  │
      │  ADVANCE 1000000     │                    │
      ├──────────────────────┼───────────────────>│
      │                      │                    │ (process events
      │                      │                    │  during [0, 1ms))
      │  DONE                │                    │
      │<─────────────────────┤                    │
      │  [events_json]       │                    │
      │<─────────────────────┤                    │
      │  DONE                │                    │
      │<─────────────────────┼────────────────────┤
      │  [events_json]       │                    │
      │<─────────────────────┼────────────────────┤
      │                      │                    │
      │  (all nodes at 1ms)  │                    │
      │  ADVANCE 2000000     │                    │
      ├─────────────────────>│                    │
      │  ADVANCE 2000000     │                    │
      ├──────────────────────┼───────────────────>│
      │  ...                 │                    │
```

**Key properties**:
- Coordinator sends `ADVANCE <target_time_us>` to all nodes
- Nodes process events in time range `[current_time, target_time)`
- Nodes respond with `DONE` followed by generated events (JSON)
- Coordinator waits for all nodes before advancing to next step
- **Result**: All nodes always synchronized to the same virtual time

### 2.2 Message Format

**Coordinator → Node**:
```
ADVANCE <target_time_us>\n
```
- `target_time_us`: Target virtual time in microseconds (e.g., `1000000` = 1 second)

**Node → Coordinator**:
```
DONE\n
<events_json>\n
```
- `DONE`: Signals completion of time advancement
- `events_json`: JSON array of events generated during advancement (may be empty `[]`)

**Example events**:
```json
[
  {
    "type": "TRANSMIT",
    "time_us": 500000,
    "src": "edge_gateway_1",
    "dst": "cloud_service",
    "payload": "...",
    "size_bytes": 1024
  },
  {
    "type": "METRIC",
    "time_us": 1000000,
    "node": "edge_gateway_1",
    "metric": "cpu_usage",
    "value": 0.42
  }
]
```

### 2.3 Initialization Protocol

**Coordinator → Node** (first message):
```
INIT <node_id> <config_json>\n
```
- `node_id`: Unique identifier for this node (e.g., `edge_gateway_1`)
- `config_json`: Configuration parameters (JSON object)

**Node → Coordinator**:
```
READY\n
```

**Example**:
```
Coordinator: INIT edge_gateway_1 {"processing_rate_mbps": 100, "seed": 42}\n
Node:        READY\n
```

---

## 3. Architecture Pattern: DeterministicNode

All socket-based nodes should follow this general architecture (shown in pseudocode):

```
class DeterministicNode {
    node_id: string
    config: object
    current_time_us: int64  // Virtual time (NOT wall-clock)
    event_queue: PriorityQueue<Event>  // Sorted by time
    rng: SeededRandom  // Deterministic RNG

    // Initialize from coordinator's INIT message
    function init(node_id, config) {
        this.node_id = node_id
        this.config = config
        this.current_time_us = 0
        this.rng = SeededRandom(config.seed)
        this.event_queue = PriorityQueue()
        this.initialize_state()
    }

    // Respond to coordinator's ADVANCE message
    function advance(target_time_us) {
        events = []

        // Process all events in time range [current_time, target_time)
        while (event_queue.peek() != null && event_queue.peek().time < target_time_us) {
            event = event_queue.pop()
            this.current_time_us = event.time
            output_events = this.handle_event(event)
            events.extend(output_events)
        }

        // Advance to target time
        this.current_time_us = target_time_us

        // Return events to coordinator
        return events
    }

    // Override this in subclasses
    function initialize_state() {
        // Set up initial state
        // Schedule initial events (e.g., periodic sampling)
    }

    // Override this in subclasses
    function handle_event(event) {
        // Process event, update state, return output events
    }

    // Helper: Schedule a future event
    function schedule_event(event) {
        assert(event.time >= this.current_time_us)
        this.event_queue.push(event)
    }

    // Helper: Generate deterministic random values
    function random() {
        return this.rng.random()
    }
}
```

**Key components**:
1. **Virtual time tracking**: `current_time_us` (never use wall-clock time)
2. **Event queue**: Sorted by time, contains all scheduled future events
3. **Seeded RNG**: Deterministic random number generator
4. **Event-driven logic**: All behavior triggered by events (not continuous loops)
5. **Explicit state**: All state stored in fields (no hidden state)

---

## 4. Determinism Techniques

### 4.1 Virtual Time (Not Wall-Clock Time)

**❌ WRONG** (wall-clock time):
```python
import time
start = time.time()  # Wall-clock time!
time.sleep(0.1)      # Real sleep!
duration = time.time() - start  # Non-deterministic!
```

**✅ CORRECT** (virtual time):
```python
class Node:
    def __init__(self):
        self.current_time_us = 0  # Virtual time

    def advance(self, target_time_us):
        delta_us = target_time_us - self.current_time_us
        # Use delta_us to update state
        self.current_time_us = target_time_us
```

### 4.2 Seeded Random Number Generators

**❌ WRONG** (non-deterministic):
```go
import "math/rand"
value := rand.Float64()  // Uses global seed, non-deterministic!
```

**✅ CORRECT** (deterministic):
```go
import "math/rand"

type Node struct {
    rng *rand.Rand
}

func NewNode(nodeID string, config Config) *Node {
    seed := hash(nodeID + config.Seed)  // Deterministic seed
    return &Node{
        rng: rand.New(rand.NewSource(seed)),
    }
}

func (n *Node) generateValue() float64 {
    return n.rng.Float64()  // Deterministic!
}
```

### 4.3 Event-Based Communication (Not Blocking I/O)

**❌ WRONG** (blocking I/O during advancement):
```cpp
std::vector<Event> advance(uint64_t target_time_us) {
    // ❌ Blocking network call during advancement!
    std::string data = http_get("http://example.com/data");
    return process(data);
}
```

**✅ CORRECT** (return events to coordinator):
```cpp
std::vector<Event> advance(uint64_t target_time_us) {
    std::vector<Event> events;

    // Return an event instead of blocking
    Event transmit_event;
    transmit_event.type = "TRANSMIT";
    transmit_event.time_us = current_time_us;
    transmit_event.dst = "cloud_service";
    transmit_event.payload = "GET /data";
    events.push_back(transmit_event);

    current_time_us = target_time_us;
    return events;
}
```

**Flow**:
1. Node returns `TRANSMIT` event to coordinator
2. Coordinator routes event through ns-3 (simulated network)
3. Coordinator delivers event to destination node at simulated arrival time
4. Destination processes event during its next `advance()`

### 4.4 Scheduled Events (Not Continuous Loops)

**❌ WRONG** (continuous loop):
```java
while (true) {  // ❌ Infinite loop!
    if (currentTimeUs % 1000000 == 0) {  // Every second
        sendData();
    }
}
```

**✅ CORRECT** (scheduled events):
```java
class Node {
    PriorityQueue<Event> eventQueue;

    void initializeState() {
        // Schedule first periodic event
        scheduleEvent(new PeriodicSampleEvent(1000000));  // At 1 second
    }

    List<Event> handleEvent(Event event) {
        if (event instanceof PeriodicSampleEvent) {
            // Process periodic sampling
            List<Event> outputs = processSample();

            // Schedule next occurrence
            scheduleEvent(new PeriodicSampleEvent(
                currentTimeUs + 1000000  // Next second
            ));

            return outputs;
        }
        return Collections.emptyList();
    }
}
```

### 4.5 Explicit State Tracking

**❌ WRONG** (hidden state in closures):
```javascript
let counter = 0;  // ❌ Hidden state outside class!

function advance(targetTimeUs) {
    counter++;  // Non-deterministic across serialization
    return [];
}
```

**✅ CORRECT** (explicit state in fields):
```javascript
class Node {
    constructor(nodeId, config) {
        this.nodeId = nodeId;
        this.currentTimeUs = 0;
        this.counter = 0;  // ✅ Explicit field
    }

    advance(targetTimeUs) {
        this.counter++;  // Deterministic, serializable
        this.currentTimeUs = targetTimeUs;
        return [];
    }
}
```

---

## 5. Implementation Examples

### 5.1 Python Example

**File**: `edge_gateway.py`

```python
#!/usr/bin/env python3
import socket
import json
import random
import heapq
from dataclasses import dataclass, asdict
from typing import List, Optional

@dataclass
class Event:
    type: str
    time_us: int
    src: str
    dst: Optional[str] = None
    payload: Optional[str] = None
    size_bytes: int = 0

    def __lt__(self, other):
        return self.time_us < other.time_us

class DeterministicNode:
    """Base class for deterministic socket-based nodes."""

    def __init__(self, node_id: str, config: dict):
        self.node_id = node_id
        self.config = config
        self.current_time_us = 0
        self.event_queue = []  # Min-heap sorted by time
        self.rng = random.Random(hash(node_id + str(config.get('seed', 0))))
        self.initialize_state()

    def initialize_state(self):
        """Override this to set up initial state and schedule initial events."""
        pass

    def advance(self, target_time_us: int) -> List[Event]:
        """Process events in [current_time, target_time) and return output events."""
        output_events = []

        # Process all events before target time
        while self.event_queue and self.event_queue[0].time_us < target_time_us:
            event = heapq.heappop(self.event_queue)
            self.current_time_us = event.time_us
            events = self.handle_event(event)
            output_events.extend(events)

        # Advance to target time
        self.current_time_us = target_time_us
        return output_events

    def handle_event(self, event: Event) -> List[Event]:
        """Override this to handle events. Return list of output events."""
        raise NotImplementedError()

    def schedule_event(self, event: Event):
        """Schedule a future event."""
        assert event.time_us >= self.current_time_us, \
            f"Cannot schedule event in the past: {event.time_us} < {self.current_time_us}"
        heapq.heappush(self.event_queue, event)

class EdgeGateway(DeterministicNode):
    """Example: Edge gateway with packet processing queue."""

    def initialize_state(self):
        self.processing_queue = []
        self.processing_rate_mbps = self.config.get('processing_rate_mbps', 100)
        self.cpu_usage = 0.0

        # Schedule periodic CPU usage metric
        self.schedule_event(Event(
            type='METRIC_REPORT',
            time_us=1_000_000,  # Every 1 second
            src=self.node_id
        ))

    def handle_event(self, event: Event) -> List[Event]:
        output = []

        if event.type == 'PACKET_ARRIVAL':
            # Add to processing queue
            self.processing_queue.append(event.payload)

            # Schedule processing completion
            processing_time_us = (event.size_bytes * 8 * 1_000_000) // (self.processing_rate_mbps * 1_000_000)
            completion_time = self.current_time_us + processing_time_us

            self.schedule_event(Event(
                type='PROCESSING_COMPLETE',
                time_us=completion_time,
                src=self.node_id,
                payload=event.payload
            ))

            # Update CPU usage
            self.cpu_usage = min(1.0, len(self.processing_queue) / 10.0)

        elif event.type == 'PROCESSING_COMPLETE':
            # Forward to cloud
            self.processing_queue.remove(event.payload)
            output.append(Event(
                type='TRANSMIT',
                time_us=self.current_time_us,
                src=self.node_id,
                dst='cloud_service',
                payload=event.payload,
                size_bytes=1024
            ))

        elif event.type == 'METRIC_REPORT':
            # Report CPU usage metric
            output.append(Event(
                type='METRIC',
                time_us=self.current_time_us,
                src=self.node_id,
                payload=json.dumps({'cpu_usage': self.cpu_usage})
            ))

            # Schedule next metric report
            self.schedule_event(Event(
                type='METRIC_REPORT',
                time_us=self.current_time_us + 1_000_000,
                src=self.node_id
            ))

        return output

def main():
    """Socket-based node main loop."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 5000))  # Coordinator address
    sock_file = sock.makefile('rw')

    node = None

    while True:
        line = sock_file.readline().strip()
        if not line:
            break

        parts = line.split(' ', 2)
        cmd = parts[0]

        if cmd == 'INIT':
            node_id = parts[1]
            config = json.loads(parts[2])
            node = EdgeGateway(node_id, config)
            sock_file.write('READY\n')
            sock_file.flush()

        elif cmd == 'ADVANCE':
            target_time_us = int(parts[1])
            events = node.advance(target_time_us)

            sock_file.write('DONE\n')
            events_json = json.dumps([asdict(e) for e in events])
            sock_file.write(events_json + '\n')
            sock_file.flush()

        elif cmd == 'SHUTDOWN':
            break

    sock.close()

if __name__ == '__main__':
    main()
```

### 5.2 Go Example

**File**: `edge_gateway.go`

```go
package main

import (
    "bufio"
    "encoding/json"
    "fmt"
    "math/rand"
    "net"
    "container/heap"
    "hash/fnv"
)

// Event represents a simulation event
type Event struct {
    Type      string `json:"type"`
    TimeUs    int64  `json:"time_us"`
    Src       string `json:"src"`
    Dst       string `json:"dst,omitempty"`
    Payload   string `json:"payload,omitempty"`
    SizeBytes int    `json:"size_bytes"`
}

// EventQueue is a priority queue of events sorted by time
type EventQueue []*Event

func (eq EventQueue) Len() int           { return len(eq) }
func (eq EventQueue) Less(i, j int) bool { return eq[i].TimeUs < eq[j].TimeUs }
func (eq EventQueue) Swap(i, j int)      { eq[i], eq[j] = eq[j], eq[i] }
func (eq *EventQueue) Push(x interface{}) { *eq = append(*eq, x.(*Event)) }
func (eq *EventQueue) Pop() interface{} {
    old := *eq
    n := len(old)
    item := old[n-1]
    *eq = old[0 : n-1]
    return item
}

// DeterministicNode is the base interface for deterministic nodes
type DeterministicNode interface {
    Init(nodeID string, config map[string]interface{})
    Advance(targetTimeUs int64) []*Event
}

// EdgeGateway implements a deterministic edge gateway node
type EdgeGateway struct {
    nodeID           string
    config           map[string]interface{}
    currentTimeUs    int64
    eventQueue       EventQueue
    rng              *rand.Rand
    processingQueue  []string
    processingRateMbps float64
    cpuUsage         float64
}

func NewEdgeGateway() *EdgeGateway {
    return &EdgeGateway{
        eventQueue: make(EventQueue, 0),
    }
}

func (eg *EdgeGateway) Init(nodeID string, config map[string]interface{}) {
    eg.nodeID = nodeID
    eg.config = config
    eg.currentTimeUs = 0
    eg.processingQueue = make([]string, 0)
    eg.cpuUsage = 0.0

    // Seeded RNG for determinism
    seed := hashString(nodeID)
    if seedVal, ok := config["seed"].(float64); ok {
        seed = int64(seedVal)
    }
    eg.rng = rand.New(rand.NewSource(seed))

    // Processing rate
    eg.processingRateMbps = 100.0
    if rate, ok := config["processing_rate_mbps"].(float64); ok {
        eg.processingRateMbps = rate
    }

    // Initialize heap
    heap.Init(&eg.eventQueue)

    // Schedule first metric report
    eg.scheduleEvent(&Event{
        Type:   "METRIC_REPORT",
        TimeUs: 1_000_000, // 1 second
        Src:    eg.nodeID,
    })
}

func (eg *EdgeGateway) Advance(targetTimeUs int64) []*Event {
    outputEvents := make([]*Event, 0)

    // Process all events before target time
    for eg.eventQueue.Len() > 0 && eg.eventQueue[0].TimeUs < targetTimeUs {
        event := heap.Pop(&eg.eventQueue).(*Event)
        eg.currentTimeUs = event.TimeUs
        events := eg.handleEvent(event)
        outputEvents = append(outputEvents, events...)
    }

    // Advance to target time
    eg.currentTimeUs = targetTimeUs
    return outputEvents
}

func (eg *EdgeGateway) handleEvent(event *Event) []*Event {
    output := make([]*Event, 0)

    switch event.Type {
    case "PACKET_ARRIVAL":
        // Add to processing queue
        eg.processingQueue = append(eg.processingQueue, event.Payload)

        // Schedule processing completion
        processingTimeUs := int64(float64(event.SizeBytes*8*1_000_000) / (eg.processingRateMbps * 1_000_000))
        completionTime := eg.currentTimeUs + processingTimeUs

        eg.scheduleEvent(&Event{
            Type:    "PROCESSING_COMPLETE",
            TimeUs:  completionTime,
            Src:     eg.nodeID,
            Payload: event.Payload,
        })

        // Update CPU usage
        eg.cpuUsage = min(1.0, float64(len(eg.processingQueue))/10.0)

    case "PROCESSING_COMPLETE":
        // Remove from queue
        for i, p := range eg.processingQueue {
            if p == event.Payload {
                eg.processingQueue = append(eg.processingQueue[:i], eg.processingQueue[i+1:]...)
                break
            }
        }

        // Forward to cloud
        output = append(output, &Event{
            Type:      "TRANSMIT",
            TimeUs:    eg.currentTimeUs,
            Src:       eg.nodeID,
            Dst:       "cloud_service",
            Payload:   event.Payload,
            SizeBytes: 1024,
        })

    case "METRIC_REPORT":
        // Report CPU usage
        metricData, _ := json.Marshal(map[string]float64{
            "cpu_usage": eg.cpuUsage,
        })
        output = append(output, &Event{
            Type:    "METRIC",
            TimeUs:  eg.currentTimeUs,
            Src:     eg.nodeID,
            Payload: string(metricData),
        })

        // Schedule next report
        eg.scheduleEvent(&Event{
            Type:   "METRIC_REPORT",
            TimeUs: eg.currentTimeUs + 1_000_000,
            Src:    eg.nodeID,
        })
    }

    return output
}

func (eg *EdgeGateway) scheduleEvent(event *Event) {
    if event.TimeUs < eg.currentTimeUs {
        panic(fmt.Sprintf("Cannot schedule event in the past: %d < %d", event.TimeUs, eg.currentTimeUs))
    }
    heap.Push(&eg.eventQueue, event)
}

func hashString(s string) int64 {
    h := fnv.New64a()
    h.Write([]byte(s))
    return int64(h.Sum64())
}

func min(a, b float64) float64 {
    if a < b {
        return a
    }
    return b
}

func main() {
    // Connect to coordinator
    conn, err := net.Dial("tcp", "localhost:5000")
    if err != nil {
        panic(err)
    }
    defer conn.Close()

    reader := bufio.NewReader(conn)
    writer := bufio.NewWriter(conn)

    node := NewEdgeGateway()

    for {
        line, err := reader.ReadString('\n')
        if err != nil {
            break
        }

        line = line[:len(line)-1] // Remove newline
        parts := splitN(line, " ", 3)
        cmd := parts[0]

        switch cmd {
        case "INIT":
            nodeID := parts[1]
            var config map[string]interface{}
            json.Unmarshal([]byte(parts[2]), &config)

            node.Init(nodeID, config)
            writer.WriteString("READY\n")
            writer.Flush()

        case "ADVANCE":
            var targetTimeUs int64
            fmt.Sscanf(parts[1], "%d", &targetTimeUs)

            events := node.Advance(targetTimeUs)

            writer.WriteString("DONE\n")
            eventsJSON, _ := json.Marshal(events)
            writer.WriteString(string(eventsJSON) + "\n")
            writer.Flush()

        case "SHUTDOWN":
            return
        }
    }
}

func splitN(s, sep string, n int) []string {
    result := make([]string, 0, n)
    for i := 0; i < n-1; i++ {
        idx := indexOf(s, sep)
        if idx == -1 {
            break
        }
        result = append(result, s[:idx])
        s = s[idx+len(sep):]
    }
    result = append(result, s)
    return result
}

func indexOf(s, substr string) int {
    for i := 0; i < len(s)-len(substr)+1; i++ {
        if s[i:i+len(substr)] == substr {
            return i
        }
    }
    return -1
}
```

### 5.3 C++ Example (Header)

**File**: `deterministic_node.h`

```cpp
#ifndef DETERMINISTIC_NODE_H
#define DETERMINISTIC_NODE_H

#include <string>
#include <vector>
#include <queue>
#include <map>
#include <random>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// Event structure
struct Event {
    std::string type;
    uint64_t time_us;
    std::string src;
    std::string dst;
    std::string payload;
    int size_bytes;

    // For priority queue (min-heap)
    bool operator>(const Event& other) const {
        return time_us > other.time_us;
    }
};

// Base class for deterministic nodes
class DeterministicNode {
protected:
    std::string node_id_;
    json config_;
    uint64_t current_time_us_;
    std::priority_queue<Event, std::vector<Event>, std::greater<Event>> event_queue_;
    std::mt19937_64 rng_;

public:
    DeterministicNode() : current_time_us_(0) {}
    virtual ~DeterministicNode() = default;

    void init(const std::string& node_id, const json& config) {
        node_id_ = node_id;
        config_ = config;
        current_time_us_ = 0;

        // Seeded RNG for determinism
        uint64_t seed = std::hash<std::string>{}(node_id);
        if (config.contains("seed")) {
            seed = config["seed"].get<uint64_t>();
        }
        rng_.seed(seed);

        initialize_state();
    }

    std::vector<Event> advance(uint64_t target_time_us) {
        std::vector<Event> output_events;

        // Process all events before target time
        while (!event_queue_.empty() && event_queue_.top().time_us < target_time_us) {
            Event event = event_queue_.top();
            event_queue_.pop();
            current_time_us_ = event.time_us;

            auto events = handle_event(event);
            output_events.insert(output_events.end(), events.begin(), events.end());
        }

        // Advance to target time
        current_time_us_ = target_time_us;
        return output_events;
    }

    virtual void initialize_state() = 0;
    virtual std::vector<Event> handle_event(const Event& event) = 0;

protected:
    void schedule_event(const Event& event) {
        if (event.time_us < current_time_us_) {
            throw std::runtime_error("Cannot schedule event in the past");
        }
        event_queue_.push(event);
    }

    double random() {
        return std::uniform_real_distribution<double>(0.0, 1.0)(rng_);
    }
};

#endif // DETERMINISTIC_NODE_H
```

---

## 6. Determinism Verification

### 6.1 Verification Test

To verify determinism, run the same simulation twice with the same seed and configuration:

```python
def verify_determinism(node_class, config, time_steps):
    """Run node twice and verify identical output."""

    def run_simulation():
        node = node_class("test_node", config)
        all_events = []
        for t in time_steps:
            events = node.advance(t)
            all_events.extend(events)
        return all_events

    # Run 1
    events1 = run_simulation()

    # Run 2 (identical config and seed)
    events2 = run_simulation()

    # Verify identical output
    assert len(events1) == len(events2), "Different number of events!"
    for i, (e1, e2) in enumerate(zip(events1, events2)):
        assert e1.type == e2.type, f"Event {i}: Different type"
        assert e1.time_us == e2.time_us, f"Event {i}: Different time"
        assert e1.payload == e2.payload, f"Event {i}: Different payload"

    print(f"✅ Determinism verified: {len(events1)} events identical")
```

### 6.2 Checklist for Deterministic Implementation

- [ ] **Virtual time**: All time tracking uses `current_time_us`, never wall-clock APIs
- [ ] **Seeded RNG**: All randomness uses seeded RNG (seed derived from node_id + config)
- [ ] **Event-driven**: All behavior triggered by events, no continuous loops
- [ ] **No blocking I/O**: All I/O represented as events returned to coordinator
- [ ] **Explicit state**: All state stored in fields, no hidden global state
- [ ] **No wall-clock sleep**: No `sleep()`, `usleep()`, `time.sleep()` calls
- [ ] **No system time**: No `time()`, `gettimeofday()`, `clock_gettime()` calls
- [ ] **No threading**: Nodes are single-threaded (coordinator handles concurrency)
- [ ] **Deterministic ordering**: Event queue sorted by time, consistent tiebreaking
- [ ] **Verification test**: Simulation runs produce identical results with same seed

---

## 7. Integration with Coordinator

### 7.1 Coordinator Configuration

**File**: `config.yaml` (example)

```yaml
simulation:
  duration_us: 10000000  # 10 seconds
  time_step_us: 1000     # 1ms steps

nodes:
  - type: socket
    id: edge_gateway_1
    executable: ./edge_gateway.py
    port: 5001
    config:
      processing_rate_mbps: 100
      seed: 42

  - type: socket
    id: edge_gateway_2
    executable: ./edge_gateway
    port: 5002
    config:
      processing_rate_mbps: 200
      seed: 43
```

### 7.2 Coordinator Pseudocode

```python
class Coordinator:
    def __init__(self, config):
        self.nodes = []
        self.current_time_us = 0

        # Start all socket nodes
        for node_config in config['nodes']:
            if node_config['type'] == 'socket':
                node = SocketNode(
                    node_config['id'],
                    node_config['executable'],
                    node_config['port']
                )
                node.init(node_config['config'])
                self.nodes.append(node)

    def run(self, duration_us, time_step_us):
        while self.current_time_us < duration_us:
            self.current_time_us += time_step_us

            # Send ADVANCE to all nodes
            for node in self.nodes:
                node.send_advance(self.current_time_us)

            # Collect events from all nodes
            all_events = []
            for node in self.nodes:
                events = node.receive_events()
                all_events.extend(events)

            # Distribute events (e.g., via ns-3)
            self.distribute_events(all_events)

    def distribute_events(self, events):
        # Route TRANSMIT events through ns-3
        # Deliver events to destination nodes
        # Log METRIC events
        pass
```

---

## 8. Common Pitfalls

### 8.1 Using Wall-Clock Time

**Problem**: Node uses `time.time()`, `clock_gettime()`, etc.

**Symptom**: Different results on each run, even with same seed.

**Fix**: Replace all wall-clock calls with virtual time tracking.

### 8.2 Non-Deterministic RNG

**Problem**: Using unseeded or globally-seeded RNG.

**Symptom**: Different random values on each run.

**Fix**: Create per-node seeded RNG instances.

### 8.3 Blocking I/O During Advancement

**Problem**: Node makes HTTP requests, file I/O, or network calls during `advance()`.

**Symptom**: Non-deterministic latencies, timing variations.

**Fix**: Return events to coordinator; let coordinator handle communication.

### 8.4 Race Conditions in Event Handling

**Problem**: Events processed in non-deterministic order (e.g., same timestamp).

**Symptom**: Different results depending on scheduling.

**Fix**: Use stable sort with deterministic tiebreaking (e.g., by node_id, then event type).

### 8.5 Hidden State

**Problem**: State stored in global variables, closures, or external files.

**Symptom**: State not properly reset between simulation runs.

**Fix**: Store all state in node object fields; implement explicit reset/init.

---

## 9. Advanced Topics

### 9.1 Event Timestamps Within Time Steps

Events generated during `advance(current, target)` can have any timestamp in `[current, target)`:

```python
def advance(self, target_time_us):
    events = []

    # Event at start of interval
    events.append(Event(
        type='START',
        time_us=self.current_time_us,  # Start of interval
        src=self.node_id
    ))

    # Event during interval
    events.append(Event(
        type='MIDDLE',
        time_us=self.current_time_us + 500,  # Midpoint
        src=self.node_id
    ))

    self.current_time_us = target_time_us
    return events
```

Coordinator sorts all events by timestamp before delivering them.

### 9.2 Inter-Node Event Delivery

**Direct delivery** (for fast statistical models):
```python
# Node A generates event for Node B
Event(type='MESSAGE', time_us=1000, src='A', dst='B', payload='data')

# Coordinator immediately delivers to B during same time step
```

**Network-routed delivery** (for realistic simulation):
```python
# Node A generates TRANSMIT event
Event(type='TRANSMIT', time_us=1000, src='A', dst='B', payload='data', size_bytes=1024)

# Coordinator routes through ns-3
latency_us = ns3.simulate_transmission('A', 'B', 1024)

# Coordinator delivers to B at time_us + latency_us
```

### 9.3 Checkpointing and Resume

For long simulations, nodes can support checkpointing:

```python
class DeterministicNode:
    def save_checkpoint(self) -> dict:
        """Return serializable state."""
        return {
            'node_id': self.node_id,
            'current_time_us': self.current_time_us,
            'rng_state': self.rng.getstate(),
            'event_queue': [asdict(e) for e in self.event_queue],
            # ... other state fields
        }

    def load_checkpoint(self, checkpoint: dict):
        """Restore from serialized state."""
        self.node_id = checkpoint['node_id']
        self.current_time_us = checkpoint['current_time_us']
        self.rng.setstate(checkpoint['rng_state'])
        self.event_queue = [Event(**e) for e in checkpoint['event_queue']]
        # ... other state fields
```

---

## 10. Summary

**Key principles for deterministic socket-based nodes**:

1. **Virtual time**: Track `current_time_us`, never use wall-clock APIs
2. **Seeded RNG**: Deterministic random number generation
3. **Event-driven**: All behavior triggered by events
4. **No blocking I/O**: Return events to coordinator
5. **Explicit state**: All state in object fields

**Socket protocol**:
- `INIT <node_id> <config>` → `READY`
- `ADVANCE <target_time_us>` → `DONE\n<events_json>`
- Events sorted by time, processed in order

**Verification**:
- Same seed + same config → identical results
- Use verification tests to catch non-determinism

**Architecture pattern**:
```
class DeterministicNode:
    current_time_us: int
    event_queue: PriorityQueue
    rng: SeededRandom

    advance(target_time_us):
        while event_queue.peek().time < target_time:
            event = event_queue.pop()
            handle_event(event)
        current_time_us = target_time_us
```

---

## References

- **architecture.md**: Core xEdgeSim architecture (federated co-simulation, lockstep algorithm)
- **python-node-determinism.md**: Python-specific determinism guide
- **implementation-guide.md**: Feature implementation details (metrics, scenarios, ns-3 integration)

