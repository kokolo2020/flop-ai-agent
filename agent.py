"""FLOP Agent v1: offline simulator. No live network or wallet operations."""
import argparse
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = Path(os.environ.get('FLOP_DB', str(BASE / 'activity.sqlite3')))
CONFIG = BASE / 'config.json'

def now():
    return datetime.now(timezone.utc).isoformat()

def init():
    with sqlite3.connect(DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created TEXT, task TEXT, status TEXT, cost_units INTEGER, receipt TEXT, output TEXT)')

def config():
    return json.loads(CONFIG.read_text())

def spent_today(c):
    day = datetime.now(timezone.utc).date().isoformat()
    return c.execute("SELECT COALESCE(SUM(cost_units),0) FROM jobs WHERE substr(created,1,10)=? AND status='completed'", (day,)).fetchone()[0]

def run(task):
    cfg = config()
    if not task.strip() or len(task)>cfg['max_prompt_chars']:
        raise ValueError('Task is empty or exceeds max_prompt_chars')
    if cfg['mode'] != 'simulation':
        raise RuntimeError('Only simulation is supported. Live FLOP API is not verified.')
    cost = cfg['simulated_cost_units_per_job']
    with sqlite3.connect(DB) as c:
        c.execute('BEGIN IMMEDIATE')
        used = spent_today(c)
        if used+cost>cfg['daily_budget_units']:
            raise RuntimeError(f'Daily budget exceeded: used={used}, next={cost}, cap={cfg["daily_budget_units"]}')
        job_id = str(uuid.uuid4())
        output = f'[SIMULATED ONLY] Task accepted: {task}. No inference was performed.'
        receipt = 'SIM-' + hashlib.sha256((job_id+task).encode()).hexdigest()[:20]
        c.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?,?)', (job_id,now(),task,'completed',cost,receipt,output))
    return {'job_id':job_id,'receipt':receipt,'simulated_cost_units':cost,'output':output,'airdrop_eligible':False}

def status():
    cfg=config()
    with sqlite3.connect(DB) as c:
        total=c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
        used=spent_today(c)
        recent=c.execute('SELECT id,created,task,status,cost_units,receipt FROM jobs ORDER BY created DESC LIMIT 10').fetchall()
    return {'mode':cfg['mode'],'wallet_public_address':cfg.get('wallet_public_address') or 'NOT CONFIGURED', 'daily_budget_units':cfg['daily_budget_units'],'used_today_units':used,'jobs_total':total,'airdrop_eligible_jobs':0,'recent_jobs':[dict(zip(('id','created','task','status','cost_units','receipt'),r)) for r in recent]}

def main():
    p=argparse.ArgumentParser(description='FLOP minimal agent offline simulator')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    r=sub.add_parser('run');r.add_argument('task')
    sub.add_parser('status')
    args=p.parse_args()
    init()
    if args.command=='init': result={'initialized':str(DB),'mode':'simulation'}
    elif args.command=='run': result=run(args.task)
    else: result=status()
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
