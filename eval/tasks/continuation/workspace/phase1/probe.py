"""The retiring calibration instrument: run once before its data is removed."""
import csv
from pathlib import Path
from statistics import mode

rows = list(csv.DictReader(Path(__file__).with_name("readings.csv").open(encoding="utf-8")))
times = [int(row["accepted_time"]) for row in rows]
width = mode([right - left for left, right in zip(times, times[1:])])
print(f"CALIBRATION shift={times[0]} width={width} tie=largest-sequence")
