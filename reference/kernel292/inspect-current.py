"""Run the established read-only kernel290 preflight in the current evidence directory."""
from pathlib import Path
source=(Path(__file__).resolve().parents[1]/'kernel291/inspect-current.py').read_text().replace('stage=291','stage=292')
exec(compile(source,__file__,'exec'))
