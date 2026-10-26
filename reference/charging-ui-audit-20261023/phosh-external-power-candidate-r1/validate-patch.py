"""Regenerate in a new private directory and apply only this patch there."""
from pathlib import Path
import contextlib,hashlib,importlib.util,io,json,shutil,subprocess
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'phosh-connection-source-r8/release-files/phosh'
OUT=Path('E:/edk2-samurai-out/charging-ui-audit-20261023/phosh-external-power-source-proof-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists()
OUT.mkdir(parents=True)
shutil.copyfile(HERE/'manager-additions.c.inc',OUT/'manager-additions.c.inc')
spec=importlib.util.spec_from_file_location('private_candidate_generator',HERE/'prepare-candidate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.HERE=OUT
with contextlib.redirect_stdout(io.StringIO()):module.main()
pins=json.loads((HERE/'source-result.json').read_bytes())['files']
for name in pins:
    assert (OUT/'candidate'/name).read_bytes()==(HERE/'candidate'/name).read_bytes(),name
assert (OUT/'external-power-marker.patch').read_bytes()==(HERE/'external-power-marker.patch').read_bytes()
tree=OUT/'apply';tree.mkdir()
for name in pins:
    p=BASE/name
    if not p.exists():continue
    target=tree/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
def linux(path):return '/mnt/e/'+str(path.resolve()).replace('\\','/')[3:]
commands=[]
for stage,flags in [('dry-run',['--dry-run']),('apply',[])]:
    argv=['wsl.exe','-d','Ubuntu','-u','root','--','patch',*flags,'--batch','-p1','-d',linux(tree),'-i',linux(HERE/'external-power-marker.patch')]
    child=subprocess.run(argv,capture_output=True)
    (OUT/(stage+'.stdout')).write_bytes(child.stdout);(OUT/(stage+'.stderr')).write_bytes(child.stderr)
    commands.append({'stage':stage,'argv':argv,'returncode':child.returncode})
    assert child.returncode==0,child.stderr.decode(errors='replace')+child.stdout.decode(errors='replace')
for name,pin in pins.items():assert sha(tree/name)==pin['candidate_sha256'],name
report={'passed':True,'regenerated_five_files_and_patch_byte_equal':True,'actual_patch_dry_run_and_apply':commands,
        'patch_sha256':sha(HERE/'external-power-marker.patch'),'all_applied_candidate_hashes_exact':True,
        'only_new_private_directory_written':True,'full_Phosh_build_or_device':False}
(HERE/'patch-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':True,'patch_result_sha256':sha(HERE/'patch-result.json')}))
