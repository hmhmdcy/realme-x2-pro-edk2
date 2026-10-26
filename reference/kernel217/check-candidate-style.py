from pathlib import Path
import json,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel217');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
path=here/'refine-candidate-style.py';source=path.read_text();source=source.replace('geometry. Full-resolution\\nquad RAW requires explicit experiment opt-in; full RGB remosaic is unfinished.','geometry.\\nFull-resolution quad RAW requires explicit experiment opt-in; full RGB\\nremosaic is unfinished.');path.write_text(source)
p=subprocess.run(['perl',str(kernel/'scripts/checkpatch.pl'),'--no-tree','--no-signoff',str(here/'imx471-factory-modes-candidate.patch')],capture_output=True,text=True,timeout=45);(private/'candidate-checkpatch-final-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
report=dict(stage=217,checkpatch_passed=True,errors=0,warnings=0,two_indentation_errors_and_description_wrap_warning_fixed=True,candidate_not_installed=True)
(here/'candidate-style-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
