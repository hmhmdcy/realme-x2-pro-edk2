from pathlib import Path
import subprocess,sys
R=Path(__file__).parent;s=(R/'stage-retained-candidate-v3.py').read_text().replace('retained-busy-v3','retained-busy-v4').replace('k265-candidate-v3','k265-candidate-v4').replace('candidate-stage-v3','candidate-stage-v4').replace('baseline-264-v3.so','baseline-264-v4.so')
p=R/'stage-retained-candidate-v4.py';assert not p.exists();p.write_text(s)
raise SystemExit(subprocess.run([sys.executable,str(p)]).returncode)

