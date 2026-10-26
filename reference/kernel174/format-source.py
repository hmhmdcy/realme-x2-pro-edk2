from pathlib import Path
import difflib, hashlib, json, subprocess

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel174')
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
name = 'sound/soc/codecs/wcd934x.c'
p = k/name
s = p.read_text()
lines = s.splitlines(True)
for i, line in enumerate(lines):
    if 'static int wcd934x_slim_port_' in line:
        column = line.expandtabs(8).index('(')+1
        j = i+1
        while lines[j].lstrip().startswith(('struct ', 'bool ')):
            lines[j] = '\t'*(column//8)+' '*(column%8)+lines[j].lstrip()
            j += 1
    if 'ret = regmap_update_bits(wcd->if_regmap,' in line and i < 2000:
        column = line.expandtabs(8).index('(')+1
        for j in [i+1,i+2]:
            lines[j] = '\t'*(column//8)+' '*(column%8)+lines[j].lstrip()
    if 'SND_SOC_DAPM_AIF_OUT("AIF' in line:
        column = line.expandtabs(8).index('(')+1
        lines[i+1] = '\t'*(column//8)+' '*(column%8)+lines[i+1].lstrip()
new = ''.join(lines)
assert ''.join(s.split()) == ''.join(new.split())
p.write_text(new)
patch_file = ref/'wcd-port-lifecycle.patch'
intro = patch_file.read_text().split('--- a/')[0]
old = (out/'before-private'/name).read_text()
patch_file.write_text(intro+''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
result = subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(patch_file)],cwd=k,capture_output=True)
(out/'checkpatch-private.log').write_bytes(result.stdout+result.stderr)
assert result.returncode == 0, result.stdout.decode()
subprocess.run(['git','diff','--check'],cwd=k,check=True)
report = json.loads((ref/'source-validation.json').read_text())
report['source_sha256'][name] = hashlib.sha256(p.read_bytes()).hexdigest()
report['checkpatch_pass'] = True
for folder in [ref,out]: (folder/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K174_CHECKPATCH_PASS',flush=True)
