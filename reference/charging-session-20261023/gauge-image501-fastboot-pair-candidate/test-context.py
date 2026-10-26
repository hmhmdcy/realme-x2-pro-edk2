"""Only changed context/profile acceptance; original seven-file fixture reused."""
from pathlib import Path
import importlib.util,json,tempfile,uuid
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('image501_operator',HERE/'fastboot-operator.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
cases=[]
def rejects(fn):
 try:fn()
 except (ValueError,FileExistsError):return
 raise AssertionError('required refusal missing')

def fixture(base):
    txn, token, boot = 'image501-fixture-operator', '7' * 64, str(uuid.uuid4())
    base = base / txn
    base.mkdir()
    contract = m.read_json(m.ACTIVATION / 'prepare-contract.json')
    guard = dict(contract['fixed_guard_fields'], transaction_id=txn, token=token,
                 boot_id=boot, kernel_version='#363 fixture', rootfs_release_sha256='1' * 64,
                 soc_serial_sha256='2' * 64, compatible_sha256='3' * 64)
    files = {}

    def put(name, value, raw=False):
        p = base / (name + '-private.json')
        p.write_text(value if raw else json.dumps(value))
        files[name] = {'path': p.name, 'sha256': m.sha(p)}
        return p

    put('guard', guard)
    remote = '/root/charging-management-20261023/' + txn
    common = dict(transaction_id=txn, token=token, boot_id=boot)
    put('quiesce_state', dict(common, terminal=True, exit_code=0, pid=111))
    put('quiesce_summary', dict(common, taint=0))
    put('quiesce_boot_id', boot + '\n', True)
    put('quiesce_process', dict(common, pid=111, startticks=12, status='absent',
        argv=['python3', '-B', remote + '/eud-quiesce.py', '--guard',
              remote + '/guard-private.json', '--commit-quiesce']))
    restart = dict(common, request_count=1, worker_sha256=m.pinned_tools()['eud-restart.py'],
        guard_sha256=files['guard']['sha256'], argv=['python3', '-B', remote + '/eud-restart.py',
        '--guard', remote + '/guard-private.json', '--commit-restart2-bootloader'])
    put('restart_claim', dict(restart, schema='samurai-eud-restart-host-claim-v1'))
    put('restart_dispatch', dict(restart, schema='samurai-eud-restart-dispatch-v1',
        state='dispatched_once', host_claim_sha256=files['restart_claim']['sha256'],
        restart_claim_intent='claimed_by_pinned_worker', restart_claim_observed=False,
        host_process=dict(pid=112, startticks=13, argv=['ssh', 'fixture'], terminal=True, returncode=255)))
    context = dict(schema='samurai-image501-fastboot-context-v1', transaction_id=txn, token=token,
                   old_boot_id=boot, guard_sha256=files['guard']['sha256'], files=files)
    path = base / 'host-context-private.json'
    path.write_text(json.dumps(context))

    def change(name, key, value):
        record = base / files[name]['path']
        obj = m.read_json(record)
        obj[key] = value
        record.write_text(json.dumps(obj))
        files[name]['sha256'] = m.sha(record)
        path.write_text(json.dumps(context))

    return path, context, change

with tempfile.TemporaryDirectory(prefix='image501-context-offline-',dir=m.PRIVATE) as tmp:
 path,context,change=fixture(Path(tmp))
 assert m.validate_context(path)==context
 cases.append('fresh_new_profile_and_unchanged_internal_dispatch_schema_accepted')
 original=json.loads(path.read_bytes())
 context['schema']='samurai-eud-fastboot-context-v1';path.write_text(json.dumps(context))
 rejects(lambda:m.validate_context(path));context.update(original);path.write_text(json.dumps(context))
 cases.append('old_eud_context_schema_refused')
 # Rebind altered evidence hashes so this tests semantics, not only digest mismatch.
 for key,value in [('candidate_logdump_sha256','0'*64),('rollback_boot_sha256','0'*64),
                   ('max_power_ma',100),('old_boot_guard_path','/var/lib/samurai/old/boot-id-private.txt')]:
  old=m.read_json(path.parent/context['files']['guard']['path'])[key]
  change('guard',key,value);context['guard_sha256']=context['files']['guard']['sha256'];path.write_text(json.dumps(context))
  rejects(lambda:m.validate_context(path))
  change('guard',key,old);context['guard_sha256']=context['files']['guard']['sha256'];path.write_text(json.dumps(context))
  assert m.validate_context(path)
  cases.append('refuse_changed_'+key)
 change('restart_dispatch','worker_sha256','0'*64)
 rejects(lambda:m.validate_context(path))
 cases.append('old_or_changed_restart_worker_cannot_bind_new_profile')
result={'passed':True,'case_count':len(cases),'cases':cases,'device_accessed':False,
 'operator_sha256':m.sha(HERE/'fastboot-operator.py'),'test_sha256':m.sha(__file__),
 'activation_pins':m.pinned_tools(),'boundary':'actual validator; reused synthetic seven-raw fixture; no USB/SSH'}
(HERE/'context-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
