"""Retain a reviewable candidate commit without changing the deployed stack."""
from pathlib import Path
import hashlib,json,subprocess
import host
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel');P=host.PRIVATE
p=W/'drivers/media/i2c/Kconfig';text=p.read_text();a=text.index('config VIDEO_LC898219XI\n');b=text.index('config VIDEO_S5KGW1\n',a)
block=text[a:b];assert block.count('depends on I2C && VIDEO_DEV\n')==1
text=text[:a]+block.replace('depends on I2C && VIDEO_DEV\n','depends on I2C && VIDEO_DEV && PM\n')+text[b:];p.write_text(text)
assert json.loads((R/'lens-callback-validation.json').read_text())['source_sha256']==hashlib.sha256((W/'drivers/media/i2c/lc898219xi.c').read_bytes()).hexdigest()
assert json.loads((R/'lens-board-validation.json').read_text())['sole_vaf_consumer_is_lens']
q=subprocess.run(['git','-C',str(W),'diff','--check'],capture_output=True);assert q.returncode==0,(q.stdout+q.stderr).decode()
q=subprocess.run(['perl',str(W/'scripts/checkpatch.pl'),'--no-tree','--file',str(W/'drivers/media/i2c/lc898219xi.c')],capture_output=True)
(P/'lens-checkpatch-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0 and b'0 errors, 0 warnings' in q.stdout
paths=['drivers/media/i2c/lc898219xi.c','drivers/media/i2c/Kconfig','drivers/media/i2c/Makefile','Documentation/devicetree/bindings/media/i2c/onnn,lc898219xi.yaml','arch/arm64/boot/dts/qcom/s5kgw1-samurai.dtsi']
subprocess.run(['git','-C',str(W),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(W),'commit','-m','media: i2c: add LC898219XI lens candidate and samurai graph'],check=True)
get=lambda *args:subprocess.check_output(['git','-C',str(W),*args],text=True).strip()
assert get('status','--porcelain')==''
patch=subprocess.check_output(['git','-C',str(W),'format-patch','-1','--stdout']);(R/'lc898219xi-candidate.patch').write_bytes(patch)
d=json.loads((R/'lens-candidate-source-validation.json').read_text());d.update(candidate_commit=get('rev-parse','HEAD'),uncommitted_candidate=False,clean_worktree=True,checkpatch_c_file_errors=0,checkpatch_c_file_warnings=0,pm_required=True,not_deployed=True)
(R/'lens-candidate-source-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
