from pathlib import Path
import importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;state=json.loads((HERE/'source-state.json').read_text())
for name in ['hardware-statistics-validation.json','awb-grid-validation.json']:assert json.loads((HERE/name).read_text())['passed']
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert not build['exit_code'] and not build['diagnostics']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mounted_build()
tree=Path(state['source']);relative=state['changed_sources'][0]
subprocess.run(['git','-C',str(tree),'diff','--check'],check=True)
subprocess.run(['git','-C',str(tree),'add',relative],check=True)
subprocess.run(['git','-C',str(tree),'commit','-m','media: camss: use a16-aligned default VFE175 metering grid'],check=True)
state.update(commit=subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip(),tracked_clean=not bool(subprocess.check_output(['git','-C',str(tree),'diff','HEAD'])),
 built=True,temporary_four_sensor_hardware_tested=True,automatic_white_balance_verified=True,source_requires_build_image_mounted=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
