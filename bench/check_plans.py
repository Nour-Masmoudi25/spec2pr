"""Check saved planner outputs without calling a model or inventing plans."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from contracts import ContractError, load_json, validate_contract


def check_plans(tasks, plans):
    results = []
    directories = sorted(Path(tasks).glob("T[0-9][0-9]"))
    if not directories:
        raise ContractError("No benchmark tasks found")
    for task in directories:
        result = {"task_id": task.name, "valid": False}
        try:
            spec = load_json(task / "spec.json")
            validate_contract("spec", spec)
            if spec["spec_id"] != task.name:
                raise ContractError("Spec ID does not match directory")
            plan = load_json(Path(plans) / f"{task.name}.json")
            validate_contract("plan", plan, spec=spec)
            result.update(valid=True, uncovered_acs=[])
        except (OSError, ValueError) as error:
            result["error"] = str(error)
        results.append(result)
    return {"kind": "saved_plan_validation", "valid": sum(r["valid"] for r in results),
            "total": len(results), "results": results,
            "limitation": "Valid structure and AC coverage do not prove model provenance or retry behavior."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", type=Path)
    parser.add_argument("plans", type=Path, help="directory containing T01.json, T02.json, ...")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        report = check_plans(args.tasks, args.plans)
        if args.report:
            with args.report.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2)
                stream.write("\n")
        print(f"{report['valid']}/{report['total']} plans valid")
        for result in report["results"]:
            if not result["valid"]:
                print(f"{result['task_id']}: {result['error']}")
        return 0 if report["valid"] == report["total"] else 1
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
