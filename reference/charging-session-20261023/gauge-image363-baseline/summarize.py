"""Read terminal private baseline evidence; never build or mount anything."""
from pathlib import Path
import hashlib, json, subprocess, sys
sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
PLAN=HERE.parents[1]/'charging-oem-audit-20261023/gauge-image363-integration-plan'
OUT=Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01')
BUILD=OUT/'build'
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
original=json.loads((OUT/'build-shared-before.json').read_bytes())
terminal=json.loads((OUT/'namespace-child-process.json').read_bytes())
assert terminal['terminal']
link=json.loads((PLAN/'link-inputs.json').read_bytes())
final=json.loads((PLAN/'final-link-inputs.json').read_bytes())
def members(archive):
    names=subprocess.check_output(['aarch64-linux-gnu-ar','t',str(archive)],text=True).splitlines()
    result=[]
    for n in names:
        p=Path(n)
        if not p.is_absolute(): p=archive.parent/p
        canonical=Path('/mnt/samurai-full282/build')
        result.append(str(p.relative_to(canonical if p.is_relative_to(canonical) else BUILD)))
    return result
actual=members(BUILD/'vmlinux.a')
stub=members(BUILD/'drivers/firmware/efi/libstub/lib.a')
all_objects={str(p.relative_to(BUILD)):sha(p) for p in BUILD.rglob('*.o') if p.is_file() and not p.is_symlink()}
old_objects={n:r['sha256'] for n,r in original.items() if n.endswith('.o') and r['kind']=='file'}
changes=[{'path':n,'before':old_objects.get(n),'after':all_objects.get(n)}
         for n in sorted(old_objects.keys()|all_objects.keys()) if old_objects.get(n)!=all_objects.get(n)]
(OUT/'all-object-delta.json').write_text(json.dumps(changes,indent=2)+'\n')
result=json.loads((OUT/'result.json').read_bytes())
result['archive_membership']={
 'vmlinux_count':len(actual),'vmlinux_exact_original_order':actual==list(link['members']),
 'libstub_count':len(stub),'libstub_exact_original_order':stub==list(final['libstub_members'])}
result['all_object_delta']=changes
result['private_receipts']={n:sha(OUT/n) for n in ['execution.json','namespace-proof.json','source-export.json',
 'namespace-command.json','namespace-child-process.json','child-state.json','commands.json','phases.json',
 'closure-original.json','all-object-delta.json','result.json'] if (OUT/n).is_file()}
for n in ['actual-leaf-delta.json','actual-link-input-delta.json','failure-link-input-delta.json','baseline-build-result.json']:
    if (OUT/n).is_file(): result['private_receipts'][n]=sha(OUT/n)
result['logs']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in OUT.glob('*.log')}
result['passed']=result['passed'] and all([result['archive_membership']['vmlinux_exact_original_order'],
                                          result['archive_membership']['libstub_exact_original_order']])
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'child_returncode':terminal['returncode'],
 'archive_membership':result['archive_membership'],'all_object_delta':changes,
 'outputs':result.get('baseline',{}).get('outputs'),
 'parent_mounts_unchanged':result['parent_mounts_unchanged'],
 'shared_trees_unchanged':result['shared_trees_unchanged']},indent=2),flush=True)
