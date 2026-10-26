from pathlib import Path
import subprocess,sys
R=Path(__file__).parent
s=(R/'stage-retained-candidate.py').read_text().replace('libgstpipewire-retained-busy-v2.so','libgstpipewire-retained-busy-v3.so').replace('/var/lib/samurai/k265-candidate','/var/lib/samurai/k265-candidate-v3').replace('candidate-stage-validation.json','candidate-stage-v3-validation.json').replace('retained-busy-v2-build-validation.json','retained-busy-v3-build-validation.json').replace("['candidate_sha256']","['plugin_sha256']")
s=s.replace("baseline=SDK/'work/pipewire265-retained-busy/core-map-lookup/baseline-264.so';assert not baseline.exists()","baseline=SDK/'work/pipewire265-retained-busy/core-map-lookup/baseline-264-v3.so';assert not baseline.exists()")
p=R/'stage-retained-candidate-v3.py';assert not p.exists();p.write_text(s)
raise SystemExit(subprocess.run([sys.executable,str(p)]).returncode)

