from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Task:
    id: str
    arrival_slot: int
    deadline: int
    load: int
    energy_cost: int
    priority: str = "normal"
    assigned_slot: Optional[int] = field(default=None, repr=False)
    assigned_server: Optional[str] = field(default=None, repr=False)
    latency_ms: Optional[float] = field(default=None, repr=False)
    met_deadline: Optional[bool] = field(default=None, repr=False)

    def is_critical(self): return self.priority == "critical"
    def is_flexible(self): return (self.deadline - self.arrival_slot) >= 5
    def deadline_slack(self): return self.deadline - self.arrival_slot
    def mark_scheduled(self, slot, server_name, latency):
        self.assigned_slot = slot
        self.assigned_server = server_name
        self.latency_ms = latency
        self.met_deadline = (slot <= self.deadline)

@dataclass
class Server:
    id: int
    name: str
    base_latency_ms: float
    max_connections: int = 20
    active_connections: int = field(default=0, repr=False)
    total_requests: int = field(default=0, repr=False)
    total_latency_ms: float = field(default=0.0, repr=False)
    _pending: list = field(default_factory=list, repr=False)

    def current_latency(self):
        utilisation = min(0.95, self.active_connections / self.max_connections)
        return self.base_latency_ms / (1 - utilisation)

    def accept(self, tick):
        import random
        lat = self.current_latency() + random.uniform(-3, 8)
        lat = max(2.0, lat)
        finish_tick = tick + max(1, int(lat / 5))
        self._pending.append(finish_tick)
        self.active_connections += 1
        self.total_requests += 1
        self.total_latency_ms += lat
        return lat

    def tick(self, current_tick):
        done = sum(1 for f in self._pending if f <= current_tick)
        self._pending = [f for f in self._pending if f > current_tick]
        self.active_connections = max(0, self.active_connections - done)

    def utilisation(self): return self.active_connections / self.max_connections
    def avg_latency(self):
        if self.total_requests == 0: return 0.0
        return self.total_latency_ms / self.total_requests

    def reset(self):
        self.active_connections = 0
        self.total_requests = 0
        self.total_latency_ms = 0.0
        self._pending = []

def make_cluster(n=5):
    latencies = [18, 28, 35, 42, 55]
    return [Server(id=i, name=f"S-{i+1:02d}", base_latency_ms=latencies[i % len(latencies)], max_connections=20) for i in range(n)]
