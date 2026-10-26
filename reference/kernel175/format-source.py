from pathlib import Path
import difflib, hashlib, json, subprocess

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175')
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');name='drivers/mfd/wcd934x.c'
p=k/name;s=p.read_text();s=s.replace('\tstruct mutex lock;','\t/* Serializes UP, DOWN and removal of status-scoped resources. */\n\tstruct mutex lock;')
lines=s.splitlines(True)
for i,line in enumerate(lines):
    if 'ret = regmap_add_irq_chip(' in line:
        col=line.expandtabs(8).index('(')+1
        lines[i+1]='\t'*(col//8)+' '*(col%8)+lines[i+1].lstrip()
p.write_text(''.join(lines))
manifest=json.loads((ref/'source-validation.json').read_text())
patch=(ref/'card-and-wcd-lifetime.patch').read_text().split('--- a/')[0]
for n in manifest['modified_this_stage']:
    before=(out/'before-private'/n).read_text();after=(k/n).read_text()
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'card-and-wcd-lifetime.patch').write_text(patch)
r=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'card-and-wcd-lifetime.patch')],cwd=k,capture_output=True)
(out/'checkpatch-private.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stdout.decode()
subprocess.run(['git','diff','--check'],cwd=k,check=True)
for n in manifest['source_sha256']:manifest['source_sha256'][n]=hashlib.sha256((k/n).read_bytes()).hexdigest()
manifest['checkpatch_pass']=True
for folder in [ref,out]:(folder/'source-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('K175_CHECKPATCH_PASS',flush=True)
