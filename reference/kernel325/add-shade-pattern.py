"""Add the explicitly documented shade bars after saturated bars proved uninformative."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE=Path('/home/cy122/x2pro-linux/camera325-gw1-tpg-kernel');p=TREE/'drivers/media/i2c/s5kgw1.c'
assert json.loads((HERE/'install-r2-validation.json').read_text())['passed']
assert not json.loads((HERE/'main-image-validation.json').read_text())['factory_profile_effect_observed']
shutil.copyfile(HERE/'kernel-build-validation.json',HERE/'kernel-build-color-bars-validation.json')
shutil.copyfile(HERE/'main-image-validation.json',HERE/'main-color-bars-image-validation.json')
shutil.copyfile(P/'install-proof.json',P/'install-r2-proof.json')
s=p.read_text();old='\t"Color Bars",\n};';new='\t"Color Bars",\n\t"Shade Color Bars",\n};\n\nstatic const u8 s5kgw1_test_pattern_values[] = { 0, 2, 3 };'
assert s.count(old)==1;s=s.replace(old,new);assert s.count('ctrl->val ? 2 : 0')==1;s=s.replace('ctrl->val ? 2 : 0','s5kgw1_test_pattern_values[ctrl->val]');p.write_text(s)
(HERE/'s5kgw1-test-pattern.patch').write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','--','drivers/media/i2c/s5kgw1.c']))
receipt=HERE/'kernel-source-validation.json';d=json.loads(receipt.read_text());d.update(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),menu={'0':'Disabled','1':'Color Bars','2':'Shade Color Bars'},register_values=[0,2,3],shade_bar_value_explicit_in_manufacturer_source=True);receipt.write_text(json.dumps(d,indent=2)+'\n')
q=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--strict','--no-tree',str(HERE/'s5kgw1-test-pattern.patch')],capture_output=True)
(HERE/'style-validation.json').write_text(json.dumps(dict(stage=325,exit_code=q.returncode,output=q.stdout.decode(),passed=q.returncode==0),indent=2)+'\n');print(q.stdout.decode());assert not q.returncode
