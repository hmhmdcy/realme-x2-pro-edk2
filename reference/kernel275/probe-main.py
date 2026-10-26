"""Verify main RAW/RGB after removing sensor ownership of VAF, preserving lens failure evidence."""
from pathlib import Path
R=Path(__file__).resolve().parent
source=(R.parent/'kernel273/probe-main.py').read_text().replace('k273','k275').replace('stage=273','stage=275')
exec(compile(source,'main275-derived.py','exec'),dict(__file__=str(R/'probe-main.py')))
