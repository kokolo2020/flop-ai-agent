"""ComputePilot pre-testnet benchmark. Offline fixture-based; no inference or FLOP spending.
Usage: python benchmark.py
       python benchmark.py --results results.jsonl
Each results JSONL row:
{"task_id":"T1","provider":"mock-A","duration_ms":120,"cost_units":2,"answer":"Paris"}
Rows are evaluations of PROVIDED outputs, not evidence of actual FLOP compute.
"""
import argparse
import json
import statistics
from pathlib import Path

FIXTURES = [
    {"task_id":"T1","task":"Capital of France?","expected":"paris"},
    {"task_id":"T2","task":"What is 7*8?","expected":"56"},
    {"task_id":"T3","task":"Chemical formula for water?","expected":"h2o"},
    {"task_id":"T4","task":"Capital of Japan?","expected":"tokyo"},
    {"task_id":"T5","task":"How many hours are in two days?","expected":"48"},
]
def evaluate(rows):
    expected = {item["task_id"]:item for item in FIXTURES}
    groups = {}
    for item in rows:
        task_id = item.get("task_id")
        provider = item.get("provider")
        if task_id not in expected or not isinstance(provider,str) or not provider:
            raise ValueError("Unknown task_id or provider")
        ms, cost = item.get("duration_ms"),item.get("cost_units")
        if isinstance(ms,bool) or isinstance(cost,bool) or not isinstance(ms,(int,float)) or not isinstance(cost,(int,float)) or ms<0 or cost<0:
            raise ValueError("Invalid cost/duration")
        g=groups.setdefault(provider,[])
        if any(row["task_id"]==task_id for row in g):
            raise ValueError("Duplicate task per provider")
        g.append(item)
    report=[]
    for provider, jobs in sorted(groups.items()):
        correct=sum(str(x.get("answer","")).strip().lower()==expected[x["task_id"]]["expected"] for x in jobs)
        completed=len(jobs)
        spend=sum(x["cost_units"] for x in jobs)
        report.append({"provider":provider,"correct":correct,"tasks_completed":completed,
            "benchmark_coverage_pct":round(100*completed/len(FIXTURES),2),
            "accuracy_pct":round(100*correct/completed,2),
            "median_latency_ms":round(statistics.median(x["duration_ms"] for x in jobs),2),
            "total_cost_units":round(spend,6),
            "cost_per_correct":round(spend/correct,6) if correct else None,
            "status":"OFFLINE_EVALUATION_ONLY","airdrop_eligible":False})
    return report
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--results",type=Path,help="JSONL of measured outputs from your own provider tests")
    args=parser.parse_args()
    if args.results:
        rows=[json.loads(line) for line in args.results.read_text().splitlines() if line.strip()]
    else:
        rows=[{"task_id":f["task_id"],"provider":"fixture-only","duration_ms":0,
               "cost_units":0,"answer":f["expected"]} for f in FIXTURES]
    print(json.dumps({"warning":"No live inference, wallet spend, or FLOP eligibility measured.",
                      "fixtures":len(FIXTURES),"results":evaluate(rows)},indent=2))
if __name__=="__main__":
    main()
