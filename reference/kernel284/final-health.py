"""Verify the actual deployed camera files, normal services and idle resources."""
from pathlib import Path

previous=Path(__file__).resolve().parents[1]/'kernel278/final-health.py'
source=previous.read_text().replace('k278-final-health','k284-final-health')
source=source.replace('report=dict(stage=278,','report=dict(stage=284,')
exec(compile(source,str(previous),'exec'),globals())
