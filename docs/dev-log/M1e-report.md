# M1e: Network Metrics Collection

**Stage:** M1e
**Date:** 2025-11-15
**Status:** IN PROGRESS

---

## Objective

Add network-tier metrics collection to enable analysis of network performance (latency, packet loss, throughput).

**Scope:**
- NetworkModel tracks and emits metrics events
- Coordinator collects network metrics
- CSV logging for network performance data
- Metrics: packets sent, delivered, dropped, average latency

**Explicitly excluded:**
- Per-node metrics (nodes already write their own CSVs)
- Real-time metrics visualization (just CSV logging)
- Advanced statistics (percentiles, distributions)

---

## Acceptance Criteria

1. ⬜ NetworkModel tracks network-level metrics
2. ⬜ LatencyNetworkModel emits packet lifecycle events
3. ⬜ Coordinator collects network metrics
4. ⬜ Network metrics logged to CSV file
5. ⬜ Metrics include: sent, delivered, dropped, latency stats
6. ⬜ Unit tests for metrics collection
7. ⬜ Integration test validates metrics accuracy
8. ⬜ Backward compatible (metrics optional)
9. ⬜ Git commit with clean implementation

---

## Design Decisions

### Metrics to Track

**Per-network metrics:**
- Total packets sent
- Total packets delivered
- Total packets dropped (by loss_rate)
- Total latency (sum for average calculation)
- Min/max/avg latency

**CSV Format:**
```csv
time_us,event_type,src,dst,latency_us
1000,packet_sent,sensor1,gateway,0
6000,packet_delivered,sensor1,gateway,5000
2000,packet_dropped,sensor2,gateway,0
```

### Implementation Approach

**Option 1: NetworkModel returns metrics with events**
- route_message() and advance_to() return (events, metrics)
- Metrics are simple dicts
- Coordinator collects and logs

**Option 2: NetworkModel has get_metrics() method**
- NetworkModel accumulates metrics internally
- Coordinator calls get_metrics() periodically
- Metrics include counters and stats

**Decision: Option 2**
- Cleaner API (doesn't change existing method signatures)
- NetworkModel owns its metrics state
- Easier to extend later

### NetworkModel Metrics Interface

```python
@dataclass
class NetworkMetrics:
    packets_sent: int = 0
    packets_delivered: int = 0
    packets_dropped: int = 0
    total_latency_us: int = 0  # For average calculation
    min_latency_us: Optional[int] = None
    max_latency_us: Optional[int] = None

    def average_latency_us(self) -> float:
        if self.packets_delivered == 0:
            return 0.0
        return self.total_latency_us / self.packets_delivered
```

**Add to NetworkModel ABC:**
```python
@abstractmethod
def get_metrics(self) -> NetworkMetrics:
    """Get current network metrics."""
    pass
```

### CSV Logging

**Filename:** `network_metrics.csv`

**Written by:** Coordinator (during simulation or at end)

**Format:**
```csv
time_us,packets_sent,packets_delivered,packets_dropped,avg_latency_us
0,0,0,0,0.0
1000000,10,10,0,5000.0
2000000,20,18,2,5500.0
```

**Alternative:** Event-based logging (one row per packet event)
- **Rejected:** Too verbose, harder to analyze trends

---

## Tests to Add

### 1. Unit Tests (tests/stages/M1e/)

**test_network_metrics.py:**
- `test_metrics_initialization()` - Metrics start at zero
- `test_metrics_track_sent()` - Sent counter increments
- `test_metrics_track_delivered()` - Delivered counter increments
- `test_metrics_track_dropped()` - Dropped counter increments
- `test_metrics_latency_stats()` - Min/max/avg calculated correctly
- `test_metrics_reset()` - Metrics reset to zero

### 2. Integration Tests

**test_coordinator_metrics_collection.py:**
- Run simulation with LatencyNetworkModel
- Verify metrics collected
- Verify CSV file written
- Verify metrics accuracy (sent = delivered + dropped)

---

## Implementation Plan

**Step 1:** Define NetworkMetrics dataclass
- Create `sim/network/metrics.py`
- Define metrics structure

**Step 2:** Extend NetworkModel interface
- Add `get_metrics()` abstract method
- Update DirectNetworkModel (return empty metrics)
- Update LatencyNetworkModel to track metrics

**Step 3:** Update LatencyNetworkModel
- Track packets sent/delivered/dropped
- Track latency statistics
- Implement get_metrics()

**Step 4:** Update coordinator
- Collect metrics periodically
- Write network_metrics.csv at end

**Step 5:** Write tests
- Unit tests for metrics tracking
- Integration test with CSV validation

---

## Known Limitations

**Intentional for M1e:**
- No per-link metrics (just network-wide totals)
- No real-time metrics reporting
- Simple CSV format (no timestamps for individual events)
- No bandwidth/throughput metrics

**Deferred:**
- Per-link breakdown (M1f or M2)
- Advanced statistics (percentiles, histograms)
- Metrics visualization

---

**Status:** IN PROGRESS
**Estimated Time:** 2 hours
**Started:** 2025-11-15
