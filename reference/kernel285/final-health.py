"""Check the existing deployment after host-only CST development."""
from pathlib import Path

previous=Path(__file__).resolve().parents[1]/'kernel278/final-health.py'
source=previous.read_text().replace('k278-final-health','k285-final-health')
source=source.replace('report=dict(stage=278,','report=dict(stage=285,')
exec(compile(source,str(previous),'exec'),globals())
