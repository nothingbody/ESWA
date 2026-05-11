from __future__ import annotations

import re
from pathlib import Path
from typing import List

from distance_matrix import build_euclidean_distance_matrix
from task_abstraction import LogisticsTask, Node


NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _numbers(line: str) -> List[float]:
    return [float(token) for token in NUMBER_RE.findall(line)]


def parse_solomon(path: str | Path, task_id: str | None = None) -> LogisticsTask:
    source = Path(path)
    lines = source.read_text(encoding="utf-8", errors="ignore").splitlines()
    vehicles = 0
    capacity = 0.0
    numeric_rows: List[List[float]] = []

    for index, line in enumerate(lines):
        upper = line.upper()
        if "NUMBER" in upper and "CAPACITY" in upper:
            for following in lines[index + 1 : index + 4]:
                values = _numbers(following)
                if len(values) >= 2:
                    vehicles = int(values[0])
                    capacity = float(values[1])
                    break
            continue
        values = _numbers(line)
        if len(values) >= 7:
            numeric_rows.append(values[:7])

    if not numeric_rows:
        raise ValueError(f"No Solomon customer rows found in {source}")
    if vehicles <= 0 or capacity <= 0:
        raise ValueError(f"Vehicle count/capacity not found in {source}")

    nodes: List[Node] = []
    for row in numeric_rows:
        node_id, x, y, demand, ready, due, service = row
        node_type = "depot" if int(node_id) == 0 else "customer"
        nodes.append(
            Node(
                node_id=int(node_id),
                x_coordinate=float(x),
                y_coordinate=float(y),
                demand=float(demand),
                ready_time=float(ready),
                due_time=float(due),
                service_time=float(service),
                node_type=node_type,
            )
        )

    depot_candidates = [node for node in nodes if node.node_type == "depot"]
    if not depot_candidates:
        raise ValueError(f"Depot node 0 not found in {source}")
    depot = depot_candidates[0]
    customers = [node for node in nodes if node.node_type != "depot"]
    task = LogisticsTask(
        task_id=task_id or source.stem,
        problem_type="VRPTW",
        depot=depot,
        nodes=customers,
        vehicles=vehicles,
        capacity=capacity,
        benchmark_meta={"source": str(source), "format": "solomon"},
    )
    return task.with_distance_matrix(build_euclidean_distance_matrix(task))


def parse_li_lim(path: str | Path, task_id: str | None = None) -> LogisticsTask:
    source = Path(path)
    rows: List[List[float]] = []
    for line in source.read_text(encoding="utf-8", errors="ignore").splitlines():
        values = _numbers(line)
        if values:
            rows.append(values)
    if len(rows) < 2:
        raise ValueError(f"No Li & Lim rows found in {source}")

    header = rows[0]
    if len(header) < 2:
        raise ValueError(f"Invalid Li & Lim header in {source}")
    vehicles = int(header[0])
    capacity = float(header[1])

    nodes: List[Node] = []
    pickup_delivery_pairs: dict[int, int] = {}
    for row in rows[1:]:
        if len(row) < 9:
            continue
        node_id, x, y, demand, ready, due, service, pickup_id, delivery_id = row[:9]
        node_type = "depot"
        pair_id = None
        if int(node_id) != 0:
            if int(delivery_id) > 0 and int(pickup_id) == 0:
                node_type = "pickup"
                pair_id = int(delivery_id)
                pickup_delivery_pairs[int(node_id)] = int(delivery_id)
            elif int(pickup_id) > 0 and int(delivery_id) == 0:
                node_type = "delivery"
                pair_id = int(pickup_id)
            else:
                node_type = "customer"
        nodes.append(
            Node(
                node_id=int(node_id),
                x_coordinate=float(x),
                y_coordinate=float(y),
                demand=float(demand),
                ready_time=float(ready),
                due_time=float(due),
                service_time=float(service),
                pair_id=pair_id,
                node_type=node_type,
            )
        )

    depot_candidates = [node for node in nodes if node.node_type == "depot"]
    if not depot_candidates:
        raise ValueError(f"Depot node 0 not found in {source}")
    depot = depot_candidates[0]
    customers = [node for node in nodes if node.node_type != "depot"]
    task = LogisticsTask(
        task_id=task_id or source.stem,
        problem_type="PDPTW",
        depot=depot,
        nodes=customers,
        vehicles=vehicles,
        capacity=capacity,
        pickup_delivery_pairs=pickup_delivery_pairs,
        benchmark_meta={"source": str(source), "format": "li_lim"},
    )
    return task.with_distance_matrix(build_euclidean_distance_matrix(task))
