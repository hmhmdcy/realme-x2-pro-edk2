"""Revalidate the unchanged deployed278 stack without replaying camera captures."""
from pathlib import Path

previous = Path(__file__).resolve().parents[1] / 'kernel278/final-health.py'
source = previous.read_text().replace('k278-final-health', 'k279-final-health')
source = source.replace('report=dict(stage=278,', 'report=dict(stage=279,')
exec(compile(source, str(previous), 'exec'), globals())
