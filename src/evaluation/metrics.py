from __future__ import annotations


def vehicle_gap(result_vehicles: int, bks_vehicles: int) -> int:
    return result_vehicles - bks_vehicles


def distance_gap(result_distance: float, bks_distance: float) -> float:
    if bks_distance <= 0:
        raise ValueError("BKS distance must be positive")
    return (result_distance - bks_distance) / bks_distance * 100.0


def improvement_ratio(initial_distance: float, final_distance: float) -> float:
    if initial_distance <= 0:
        raise ValueError("Initial distance must be positive")
    return (initial_distance - final_distance) / initial_distance * 100.0
