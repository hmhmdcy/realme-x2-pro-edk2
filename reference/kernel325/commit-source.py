from pathlib import Path
import hashlib,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera325-gw1-tpg-kernel')
assert json.loads((HERE/'install-r3-validation.json').read_text())['passed'] and json.loads((HERE/'main-image-validation.json').read_text())['passed']
status=subprocess.check_output(['git','-C',str(TREE),'status','--porcelain','--untracked-files=no'],text=True).splitlines();assert status==[' M drivers/media/i2c/s5kgw1.c']
source=TREE/'drivers/media/i2c/s5kgw1.c';receipt=HERE/'kernel-source-validation.json';d=json.loads(receipt.read_text());assert hashlib.sha256(source.read_bytes()).hexdigest()==d['source_sha256']
subprocess.run(['git','-C',str(TREE),'add','drivers/media/i2c/s5kgw1.c'],check=True)
q=subprocess.run(['git','-C',str(TREE),'commit','-m','media: i2c: s5kgw1: add standard test-pattern control'],capture_output=True)
(host.PRIVATE/'source-commit.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
commit=subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip();assert not subprocess.check_output(['git','-C',str(TREE),'status','--porcelain','--untracked-files=no'])
d.update(commit=commit,built=True,installed=True);receipt.write_text(json.dumps(d,indent=2)+'\n')
(HERE/'source-commit-validation.json').write_text(json.dumps(dict(stage=325,tree=str(TREE),branch='samurai-gw1-tpg325',commit=commit,parent=d['base_commit'],tracked_clean=True,only_sensor_driver_changed=True,pushed=False),indent=2)+'\n')
shutil.copyfile(host.PRIVATE/'install-proof.json',host.PRIVATE/'install-r3-proof.json')
print(json.dumps(dict(commit=commit,tracked_clean=True,installed=True),indent=2))
