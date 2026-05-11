from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class RouteSolution:
    solution_id: str
    routes: List[List[int]]
    unserved_nodes: List[int] = field(default_factory=list)
    total_distance: float = 0.0
    vehicle_number: int = 0
    feasible: bool = False
    violations: List[Dict[str, object]] = field(default_factory=list)
    runtime: float = 0.0
    generator_name: str = ""
    repair_history: List[str] = field(default_factory=list)

    def served_nodes(self) -> List[int]:
        return [node_id for route in self.routes for node_id in route]

    def copy(self, solution_id: str | None = None) -> "RouteSolution":
        return RouteSolution(
            solution_id=solution_id or self.solution_id,
            routes=[route[:] for route in self.routes],
            unserved_nodes=self.unserved_nodes[:],
            total_distance=self.total_distance,
            vehicle_number=self.vehicle_number,
            feasible=self.feasible,
            violations=[violation.copy() for violation in self.violations],
            runtime=self.runtime,
            generator_name=self.generator_name,
            repair_history=self.repair_history[:],
        )
