from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Node:
    node_id: int
    x_coordinate: float
    y_coordinate: float
    demand: float
    ready_time: float
    due_time: float
    service_time: float
    pair_id: Optional[int] = None
    node_type: str = "customer"


@dataclass
class LogisticsTask:
    task_id: str
    problem_type: str
    depot: Node
    nodes: List[Node]
    vehicles: int
    capacity: float
    distance_matrix: List[List[float]] = field(default_factory=list)
    pickup_delivery_pairs: Dict[int, int] = field(default_factory=dict)
    benchmark_meta: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._node_index = {node.node_id: node for node in [self.depot, *self.nodes]}

    @property
    def node_ids(self) -> List[int]:
        return [node.node_id for node in self.nodes]

    def node_by_id(self, node_id: int) -> Node:
        return self._node_index[node_id]

    def all_nodes(self) -> List[Node]:
        return [self.depot, *self.nodes]

    def with_distance_matrix(self, matrix: List[List[float]]) -> "LogisticsTask":
        self.distance_matrix = matrix
        return self
