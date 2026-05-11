from __future__ import annotations

try:
    from experiments._bootstrap import ensure_project_paths
except ModuleNotFoundError:  # Direct script execution: python experiments/run_binary_typed_verifier_ablation.py
    from _bootstrap import ensure_project_paths

ensure_project_paths()

import argparse
import csv
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from data_parser import parse_solomon
from fast_thinking import greedy_insertion, nearest_neighbor, regret_insertion
from fast_thinking.common import best_insertion
from reflective_optimization.relocate_search import relocate_search
from reflective_optimization.repair_insertion import repair_insertion
from reflective_optimization.route_elimination import route_elimination
from reflective_optimization.route_merge import route_merge
from reflective_optimization.two_opt import two_opt
from route_solution import RouteSolution
from task_abstraction import LogisticsTask
from verification.route_feasibility import VerificationResult, verify_solution


GENERATORS = {
    "nearest_neighbor": nearest_neighbor,
    "greedy_insertion": greedy_insertion,
    "regret_insertion": regret_insertion,
}


def _has_violation(result: VerificationResult, violation_type: str) -> bool:
    return any(violation.get("type") == violation_type for violation in result.violations)


def _blind_content_repair(task, solution: RouteSolution) -> RouteSolution:
    """Repair route content without consuming typed verifier records."""
    repaired = solution.copy(solution_id=f"{solution.solution_id}:binary_repair")
    valid_nodes = set(task.node_ids)
    seen: set[int] = set()
    clean_routes: list[list[int]] = []
    for route in repaired.routes:
        clean_route: list[int] = []
        for node_id in route:
            if node_id in valid_nodes and node_id not in seen:
                clean_route.append(node_id)
                seen.add(node_id)
        if clean_route:
            clean_routes.append(clean_route)
    repaired.routes = clean_routes

    missing = sorted(valid_nodes - seen, key=lambda node_id: (task.node_by_id(node_id).due_time, node_id))
    for node_id in missing:
        insertion = best_insertion(task, repaired.routes, node_id)
        if insertion is None:
            repaired.routes.append([node_id])
            repaired.repair_history.append(f"binary_new_route:{node_id}")
        else:
            route_index, position, _ = insertion
            repaired.routes[route_index].insert(position, node_id)
            repaired.repair_history.append(f"binary_insert:{node_id}@{route_index}:{position}")
    verify_solution(task, repaired)
    return repaired


def _local_improve(task, solution: RouteSolution) -> RouteSolution:
    relocated = relocate_search(task, solution)
    return two_opt(task, relocated)


def _row(
    task: LogisticsTask,
    generator_name: str,
    verifier_variant: str,
    solution: RouteSolution,
    runtime: float,
    typed_feedback: bool,
    action_rules: bool,
    route_elimination_called: bool,
) -> dict[str, str]:
    result = verify_solution(task, solution)
    return {
        "dataset": task.task_id,
        "generator": generator_name,
        "variant": verifier_variant,
        "verifier_variant": verifier_variant,
        "method": f"{generator_name}+{verifier_variant}",
        "vehicles": str(result.vehicle_number),
        "distance": f"{result.total_distance:.6f}",
        "feasible": str(result.feasible),
        "violations": str(len(result.violations)),
        "runtime": f"{runtime:.6f}",
        "typed_feedback": str(typed_feedback),
        "action_rules": str(action_rules),
        "route_elimination_called": str(route_elimination_called),
    }


def run_instance(instance_path: Path, generator_names: list[str]) -> list[dict[str, str]]:
    task = parse_solomon(instance_path)
    rows: list[dict[str, str]] = []
    for generator_name in generator_names:
        generator = GENERATORS[generator_name]
        fast = generator(task)
        fast_result = verify_solution(task, fast)

        started = time.perf_counter()
        binary = _blind_content_repair(task, fast)
        binary = route_merge(task, binary)
        binary = _local_improve(task, binary)
        rows.append(
            _row(
                task,
                generator_name,
                "binary_feasibility_only",
                binary,
                time.perf_counter() - started,
                typed_feedback=False,
                action_rules=False,
                route_elimination_called=False,
            )
        )

        started = time.perf_counter()
        typed = repair_insertion(task, fast, fast_result)
        typed = route_merge(task, typed)
        typed = _local_improve(task, typed)
        rows.append(
            _row(
                task,
                generator_name,
                "typed_diagnostics_only",
                typed,
                time.perf_counter() - started,
                typed_feedback=True,
                action_rules=False,
                route_elimination_called=False,
            )
        )

        started = time.perf_counter()
        typed_action = repair_insertion(task, fast, fast_result)
        typed_action = route_merge(task, typed_action)
        typed_action_result = verify_solution(task, typed_action)
        route_elimination_called = _has_violation(typed_action_result, "vehicle_count") or len(typed_action.routes) > 1
        if route_elimination_called:
            typed_action = route_elimination(task, typed_action)
        typed_action = _local_improve(task, typed_action)
        rows.append(
            _row(
                task,
                generator_name,
                "typed_action_rules",
                typed_action,
                time.perf_counter() - started,
                typed_feedback=True,
                action_rules=True,
                route_elimination_called=route_elimination_called,
            )
        )
    return rows


def _run_one(payload: tuple[str, list[str]]) -> tuple[str, list[dict[str, str]]]:
    path_text, generator_names = payload
    path = Path(path_text)
    return path.name, run_instance(path, generator_names)


def _parse_generators(value: str) -> list[str]:
    if value == "all":
        return list(GENERATORS)
    names = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [name for name in names if name not in GENERATORS]
    if unknown:
        raise ValueError(f"Unknown generator(s): {unknown}. Valid: {sorted(GENERATORS)} or all")
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description="Run binary-vs-typed verifier ablation on Solomon instances.")
    parser.add_argument("instance_dir", type=Path)
    parser.add_argument("--instances", nargs="*", default=[])
    parser.add_argument("--generators", default="nearest_neighbor")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("results/tables/binary_typed_verifier_ablation.csv"))
    args = parser.parse_args()

    generator_names = _parse_generators(args.generators)
    if args.instances:
        instance_paths = [args.instance_dir / name for name in args.instances]
    else:
        instance_paths = sorted(args.instance_dir.glob("*.txt"))
    missing = [str(path) for path in instance_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing instances: {missing}")
    if not instance_paths:
        raise FileNotFoundError(f"No .txt instances found in {args.instance_dir}")

    rows: list[dict[str, str]] = []
    if args.workers <= 1:
        for index, path in enumerate(instance_paths, start=1):
            print(f"[{index}/{len(instance_paths)}] {path.name}", flush=True)
            rows.extend(run_instance(path, generator_names))
    else:
        payloads = [(str(path), generator_names) for path in instance_paths]
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_run_one, payload) for payload in payloads]
            for index, future in enumerate(as_completed(futures), start=1):
                name, part_rows = future.result()
                print(f"[{index}/{len(instance_paths)}] {name}", flush=True)
                rows.extend(part_rows)

    rows.sort(key=lambda row: (row["dataset"], row["generator"], row["verifier_variant"]))
    if not rows:
        raise ValueError("No ablation result rows were produced")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output} rows={len(rows)}", flush=True)


if __name__ == "__main__":
    main()
