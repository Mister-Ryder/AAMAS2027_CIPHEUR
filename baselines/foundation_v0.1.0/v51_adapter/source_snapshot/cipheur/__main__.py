import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from .pipeline import load_config, preflight, run, write_json
from .model import Graph
from .programs import Program, schedule


def main():
    parser = argparse.ArgumentParser(description="CIP-Heur research foundation")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "run"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--config", default="configs/smoke.json")
        if name == "run":
            cmd.add_argument("--output")
    deploy = commands.add_parser("schedule")
    deploy.add_argument("--graph", required=True)
    deploy.add_argument("--program", required=True)
    deploy.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "schedule":
            graph = Graph.from_dict(json.loads(Path(args.graph).read_text(encoding="utf-8-sig")))
            program = Program(**json.loads(Path(args.program).read_text(encoding="utf-8-sig")))
            result = schedule(graph, program)
            write_json(Path(args.output), result)
            print(json.dumps({"feasible": result["feasible"], "value": result["value"]}))
        else:
            config = load_config(args.config)
            if args.command == "preflight":
                result = preflight(config)
            else:
                target = args.output or f"output/run_{datetime.now():%Y%m%d_%H%M%S_%f}"
                result = run(config, target)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
