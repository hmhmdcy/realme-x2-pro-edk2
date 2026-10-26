from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel');d=json.loads((R/'source-candidate-validation.json').read_text())
assert json.loads((R/'cci-power-callback-validation.json').read_text())['source_sha256']==d['source_files_sha256']['drivers/i2c/busses/i2c-qcom-cci.c']
assert json.loads((R/'current-module-build-validation.json').read_text())['source_sha256']==d['source_files_sha256']['drivers/i2c/busses/i2c-qcom-cci.c']
assert json.loads((R/'board-validation.json').read_text())['shared_cci_io_supply_matches_sensor_io']
for n,sha in d['source_files_sha256'].items():assert hashlib.sha256((W/n).read_bytes()).hexdigest()==sha
subprocess.run(['git','-C',str(W),'diff','--check'],check=True)
subprocess.run(['git','-C',str(W),'add','--',*d['source_files_sha256']],check=True)
subprocess.run(['git','-C',str(W),'commit','-m','i2c: qcom-cci: manage shared bus IO power and removal lifetime'],check=True)
get=lambda *args:subprocess.check_output(['git','-C',str(W),*args],text=True).strip();assert get('status','--porcelain')==''
(R/'cci-io-candidate.patch').write_bytes(subprocess.check_output(['git','-C',str(W),'format-patch','-1','--stdout']))
d.update(candidate_commit=get('rev-parse','HEAD'),clean_worktree=True,not_built_or_deployed=False,built_not_deployed=True);(R/'source-candidate-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
