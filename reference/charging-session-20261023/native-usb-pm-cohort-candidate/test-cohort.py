"""Affected single-USB manifest and exact two-member archive boundaries only."""
from pathlib import Path
import copy,gzip,hashlib,importlib.util,io,json,sys,tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_pm_cohort',HERE/'cohort.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
pins=json.loads((HERE/'input-pins.json').read_bytes())
old=json.loads(c.pinned(pins['base_manifest']).read_bytes())
new_hash=pins['new_USB']['sha256'];target=old['modules'][c.USB]['target']
cases=[]
def test(name,fn):fn();cases.append(name)
def reject(fn):
    try:fn()
    except (ValueError,tarfile.TarError,EOFError):return
    raise AssertionError('expected explicit rejection')
def manifest_exact():
    original=copy.deepcopy(old);new=c.make_manifest(old,new_hash)
    assert old==original
    restored=copy.deepcopy(new);restored['adapter_revision']=old['adapter_revision']
    restored['modules'][c.USB]['sha256']=old['modules'][c.USB]['sha256']
    restored['installed_files'][target]=old['installed_files'][target]
    assert restored==old
test('single USB three-field delta; all original protection/limits/files retained',manifest_exact)
def caps_and_revision():
    for key,value in [('default_input_cap_ua',1500000),('adapter_revision','future'),('source_budget_enforced',False)]:
        bad=copy.deepcopy(old);bad[key]=value;reject(lambda:c.make_manifest(bad,new_hash))
test('wrong original caps/revision/source-enforcement rejected',caps_and_revision)
def extra_manifest():
    new=c.make_manifest(old,new_hash)
    for mutate in [lambda x:x['modules']['samurai-gauge-protection'].update(sha256=new_hash),
                   lambda x:x['installed_files'].update({'/tmp/extra':new_hash})]:
        bad=copy.deepcopy(new);mutate(bad);reject(lambda:c.check_manifest_delta(old,bad,new_hash))
test('extra protection or installed-file changes rejected',extra_manifest)
files={target:b'USB-module-fixture',c.MANIFEST:c.encode(c.make_manifest(old,new_hash))}
test('two exact regular forward members accepted',lambda:c.check_archive(c.archive(files),files))
def rollback():
    back={target:b'old-USB-fixture',c.MANIFEST:c.pinned(pins['base_manifest']).read_bytes()}
    raw=c.archive(back);c.check_archive(raw,back)
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as t:assert t.extractfile(c.MANIFEST.lstrip('/')).read()==back[c.MANIFEST]
test('rollback retains exact original manifest bytes',rollback)
def altered_tar(kind):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as t:
        entries=list(files.items())
        if kind=='duplicate':entries.append(entries[0])
        if kind=='extra':entries.append(('/lib/extra-protection.ko',b'extra'))
        for i,(name,raw) in enumerate(entries):
            m=tarfile.TarInfo(name.lstrip('/'));m.uid=m.gid=0;m.uname=m.gname='root';m.mode=0o600;m.mtime=0;m.size=len(raw)
            if i==0 and kind=='symlink':m.type=tarfile.SYMTYPE;m.linkname='/tmp/elsewhere';m.size=0
            if i==0 and kind=='mode':m.mode=0o666
            t.addfile(m,io.BytesIO(raw) if m.isfile() else None)
    return gzip.compress(stream.getvalue(),mtime=0)
for kind in ['duplicate','extra','symlink','mode']:
    test('archive rejects '+kind,lambda kind=kind:reject(lambda:c.check_archive(altered_tar(kind),files)))
test('archive rejects substituted file bytes',lambda:reject(lambda:c.check_archive(c.archive(files),{**files,target:b'wrong'})))
report=dict(passed=True,actual_package_boundary_cases=len(cases),cases=cases,
    cohort_source_sha256=c.file_sha(HERE/'cohort.py'),test_source_sha256=c.file_sha(Path(__file__)),
    reused_identity_parser_source_sha256=c.file_sha(c.METHOD),old_module_tests_or_builds_repeated=False,
    device_or_build_SDK_Git_used=False)
with (HERE/'test-result.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report,indent=2))
