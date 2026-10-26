from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;state=json.loads((HERE/'source-state.json').read_text());tree=Path(state['source']);directory=Path('drivers/media/platform/qcom/camss')
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert build['exit_code']==0 and not build['diagnostics']
assert json.loads((HERE/'register-validation.json').read_text())['passed']
assert json.loads((HERE/'pattern-r2-image-validation.json').read_text())['passed']
names=[directory/n for n in ['Makefile','camss-vfe-175-ccm.c','camss-vfe-175-ccm.h','camss-vfe-175-pixel.c','camss-vfe-17x.c']]+[Path('include/uapi/linux/qcom-camss-config.h')]
subprocess.run(['git','-C',str(tree),'diff','--check'],check=True)
subprocess.run(['git','-C',str(tree),'add',*[str(n) for n in names]],check=True)
subprocess.run(['git','-C',str(tree),'commit','-m','media: camss: support VFE175 colour correction parameters'],check=True)
commit=subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()
assert not subprocess.check_output(['git','-C',str(tree),'diff','HEAD'])
state.update(commit=commit,tracked_clean=True,source_sha256={str(n):hashlib.sha256((tree/n).read_bytes()).hexdigest() for n in names},built=True,temporary_hardware_tested=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=334,commit=commit,tracked_clean=True,built=True,temporary_hardware_tested=True,installed=False)))
