"""Read current deployed identities and idle camera resources; no capture or changes."""
from pathlib import Path

previous=Path(__file__).resolve().parents[1]/'kernel278/final-health.py'
source=previous.read_text().replace('k278-final-health','k282-final-health')
source=source.replace('report=dict(stage=278,','report=dict(stage=282,')
exec(compile(source,str(previous),'exec'),globals())
