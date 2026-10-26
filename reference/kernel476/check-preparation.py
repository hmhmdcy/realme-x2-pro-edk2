"""Static/local-only audit of the generated476 template and frozen tool inputs."""
from pathlib import Path
import ast,hashlib,importlib.util,json,re,sys,tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel476')
spec=importlib.util.spec_from_file_location('check476_guard',HERE.parent/'kernel284/storage.py')
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.mounted_build()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
last=json.loads((P/'prepared-last-private.json').read_text());work=Path(last['work'])
assert last['passed'] and not last['deployable']
manifest=json.loads((work/'manifest.json').read_text());mapping=json.loads((work/'payload-files-private.json').read_text())
assert all(sha(mapping[name])==digest for name,digest in manifest.items())
with tarfile.open(work/'control-delay-payload.tar.gz','r:gz') as archive:
    assert set(archive.getnames())==set(mapping)
    for item in archive.getmembers():
        assert item.isfile() and not Path(item.name).is_absolute() and '..' not in Path(item.name).parts
        assert hashlib.sha256(archive.extractfile(item).read()).hexdigest()==sha(mapping[item.name])
worker=(work/'worker.py').read_text()
assert worker.index("assert plan['deployable']")<worker.index("dev=Path('/sys/bus/platform/devices/ac10000.icp')")
order=["for n in names:run(['rmmod',n]", "run(['rmmod','s5k3m5'],'remove-sensor')",
       "run(['insmod',str(root/proof['sensor']['file'])],'load-sensor')", "for n in reversed(names):run(['insmod'"]
assert [worker.index(x) for x in order]==sorted(worker.index(x) for x in order)
restore=["for n in names:\n    if Path('/sys/module',n).exists()", "run(['rmmod','s5k3m5'],'cleanup-sensor')", "run(['modprobe','s5k3m5'],'restore-sensor')", "run(['modprobe','qcom_camss'],'restore-formal')"]
assert [worker.index(x) for x in restore]==sorted(worker.index(x) for x in restore)
for path in HERE.glob('*.py'):ast.parse(path.read_text())
for name,path in mapping.items():
    if name.endswith('.py'):ast.parse(Path(path).read_text())
queries=list((P/'preflight').rglob('query-private.py'));assert queries
query=queries[-1].read_text();assert 'Mainline owner-return required before any device query' in query
assert '#363 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026' in query
request=json.loads((queries[-1].parent/'request-private.json').read_text());assert not request['bound']
assert request['expected']['library_sha256']=='0884c73489815132b5f180c303ab5ed2edc4c52f0f7b191365054aa855849a48'
tools=json.loads((HERE.parent/'kernel472/tools-build-validation.json').read_text())
assert all(sha(row['path'])==row['sha256'] for row in tools['tools'])
report=dict(stage=476,passed=True,worker_ast_valid=True,unbound_rejected_before_inventory=True,
    controlled_load_restore_order_preserved=True,payload_archive_members_verified=len(mapping),
    latest_offline_template=work.name,archive_sha256=sha(work/'control-delay-payload.tar.gz'),
    static_readonly_preflight_rendered=True,preflight_executed=False,default_formal_expected_unchanged=True,
    sources={p.name:sha(p) for p in sorted(HERE.iterdir()) if p.suffix in ['.py','.md']},
    tools472_unchanged=True,no_sdk=True,no_build=True,no_ssh=True,no_upload=True,no_target_worker_execution=True,
    mode2_physical_delay_measured=False)
(HERE/'execution-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
