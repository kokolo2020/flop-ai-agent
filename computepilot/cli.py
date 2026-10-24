"""Run: python -m computepilot.cli run 'Your task'."""
import argparse
import json
from .engine import execute, verify_receipt

def main():
    p = argparse.ArgumentParser(description="ComputePilot local receipt engine · V6 encoding, unsigned integrity only")
    p.add_argument("command", choices=["run", "verify"])
    p.add_argument("value", help="Task text for run; JSON receipt file for verify")
    p.add_argument("--output", help="Output text file for receipt verification")
    p.add_argument("--provider", default="simulation", choices=["simulation", "live", "flop"])
    args = p.parse_args()
    if args.command == "run":
        print(json.dumps(execute(args.value, args.provider), indent=2))
    else:
        if not args.output:
            p.error("verify requires --output FILE")
        from pathlib import Path
        receipt = json.loads(Path(args.value).read_text())
        output = Path(args.output).read_text()
        ok = verify_receipt(receipt, output)
        print("PASS" if ok else "FAIL")
        raise SystemExit(0 if ok else 1)
if __name__ == "__main__":
    main()
