from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
manifest=json.loads((ref/'source-validation.json').read_text());name='sound/soc/codecs/wcd934x.c'
before=(out/'before-private'/name).read_text()
assert hashlib.sha256(before.encode()).hexdigest()==manifest['source_sha256'][name]
p=k/name;s=p.read_text();assert s.count('static int wcd934x_init_slim_interface(')==1
shutil.copyfile(out/'checkpatch-private.log',out/'checkpatch-interface-first-private.log')
lines=s.splitlines(True)
for i,line in enumerate(lines):
    if 'static int wcd934x_init_slim_interface(' in line or 'wcd->if_regmap = regmap_init_slimbus(' in line:
        col=line.expandtabs(8).index('(')+1
        lines[i+1]='\t'*(col//8)+' '*(col%8)+lines[i+1].lstrip()
p.write_text(''.join(lines))
manifest['modified_this_stage'].append(name)
manifest['before_sha256'][name]=hashlib.sha256(before.encode()).hexdigest()
manifest['codec_interface_regmap_owned_by_codec_dev_and_exit_before_put']=True
patch=(ref/'card-and-wcd-lifetime.patch').read_text().split('--- a/')[0]
for n in manifest['modified_this_stage']:
    patch+=''.join(difflib.unified_diff((out/'before-private'/n).read_text().splitlines(True),(k/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'card-and-wcd-lifetime.patch').write_text(patch)
r=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'card-and-wcd-lifetime.patch')],cwd=k,capture_output=True)
(out/'checkpatch-private.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stdout.decode()
subprocess.run(['git','diff','--check'],cwd=k,check=True)
for n in manifest['source_sha256']:manifest['source_sha256'][n]=hashlib.sha256((k/n).read_bytes()).hexdigest()
for folder in [ref,out]:(folder/'source-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('K175_CODEC_INTERFACE_CHECKPATCH_PASS',flush=True)
