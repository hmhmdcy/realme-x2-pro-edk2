"""Check the unchanged device after 288 host integration work."""
from pathlib import Path

previous=Path(__file__).resolve().parents[1]/'kernel278/final-health.py'
s=previous.read_text().replace('k278-final-health','k288-final-health').replace('report=dict(stage=278,','report=dict(stage=288,')
exec(compile(s,str(previous),'exec'),globals())
