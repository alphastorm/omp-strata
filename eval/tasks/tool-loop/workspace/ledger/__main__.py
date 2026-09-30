import argparse
import json
from datetime import datetime
from pathlib import Path
from .report import report

parser = argparse.ArgumentParser()
parser.add_argument("csv", type=Path)
parser.add_argument("--start", required=True, type=datetime.fromisoformat)
parser.add_argument("--end", required=True, type=datetime.fromisoformat)
args = parser.parse_args()
print(json.dumps(report(args.csv, args.start, args.end), sort_keys=True))
