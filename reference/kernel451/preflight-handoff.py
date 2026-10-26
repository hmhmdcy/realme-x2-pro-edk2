"""Render a read-only query; live mode requires a new mainline owner return.

No staging, launch, phone file writes, guard adoption, service/module/USB action.
Only this script's PC-private output directory receives successful observations.
"""
from pathlib import Path
import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import re
import secrets
import shlex
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel451/preflight-handoff')
GUARD = '/var/lib/samurai/k449-adopted/boot-id-private.txt'
BODY_SHA = 'a65f6326fc2366e8bd0b225c1399c386d0aa86f83260d28e57e02ed04e279fff'
OBSERVER_SHA = '3a5716a62b817fc355343c677de73e298c421644e9e02c7438c0e58289f3fe50'
NEW_FILES = {'preflight-handoff.py', 'PREFLIGHT-NEXT.md', 'preflight-offline-validation.json'}
CHARGING_KEYS = {'manifest_sha256','notes','limits','source_type','source_budget_ua',
                 'native_udc_allowance_ua','gadget_maxpower_ma','service_enabled',
                 'native_retained','control_enabled'}
IDLE = ['users','running','fatal','pinned','orphans','failed','cancelled','first_error']
RELEASED = ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups',
            'remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped',
            'imported_buffers','imported_bytes','watchdogs','protocol_errors','cleanup_error','pc_error']
DEVICES = ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc)


def stamp():
    return utc().isoformat().replace('+00:00','Z')


def window_valid(value):
    m = re.fullmatch(r'k(?:451-proxy-comparison|452-full-diagnostic)-r([1-9]|1[0-9]|20)',value)
    assert m, 'Unsupported window_id'


def local_path(value):
    path = Path(value)
    assert path.is_absolute() and path.is_file() and not path.is_symlink()
    assert path.resolve().is_relative_to(Path('/mnt/e/edk2-samurai-out').resolve()), 'Owner evidence must remain private'
    return path


def validate_owner(owner, window, check_files=True):
    window_valid(window)
    assert owner['schema'] == 'samurai-camera-owner-return-v1'
    assert owner['from_owner']=='charging' and owner['to_owner']=='camera'
    for key in ['released','original_key_verified','charging_worker_exited','no_concurrent_owner']:
        assert owner[key] is True, key
    assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',owner['return_id'])
    assert window in owner['authorized_window_ids']
    assert len(set(owner['authorized_window_ids']))==len(owner['authorized_window_ids'])
    for item in owner['authorized_window_ids']: window_valid(item)
    issued=datetime.fromisoformat(owner['issued_at_utc'].replace('Z','+00:00'))
    assert issued.tzinfo is not None and 0 <= (utc()-issued).total_seconds() <= 3600, 'Owner return is stale or future-dated'
    assert str(uuid.UUID(owner['boot_id']))==owner['boot_id']
    assert owner['boot_guard_path']==GUARD, 'Existing k449 guard required; never adopt a guard here'
    for key in ['charging_manifest_sha256','provenance_sha256']:
        assert re.fullmatch(r'[0-9a-f]{64}',owner[key])
    if 'charging' in owner:
        assert set(owner['charging'])==CHARGING_KEYS
        assert owner['charging']['manifest_sha256']==owner['charging_manifest_sha256']
    if check_files:
        manifest=local_path(owner['charging_manifest_private'])
        provenance=local_path(owner['provenance_private'])
        assert sha(manifest)==owner['charging_manifest_sha256']
        assert sha(provenance)==owner['provenance_sha256']
        assert isinstance(json.loads(manifest.read_bytes()),dict), 'Complete manifest JSON required'
        assert isinstance(json.loads(provenance.read_bytes()),dict)


def inputs():
    formal=json.loads((HERE.parent/'kernel440/current-state-validation.json').read_text())
    restored=json.loads((HERE.parent/'kernel444/current-state-validation.json').read_text())
    proof=json.loads((PRIVATE.parents[1]/'kernel440/install-proof-r3-private.json').read_text())
    assert formal['passed'] and formal['installed'] and restored['passed']
    assert proof['packages']==formal['packages']
    modules={row['module']:dict(path=row['path'],sha256=row['new_sha256'],note=row['new_note_sha256']) for row in proof['modules']}
    assert set(modules)=={'qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core'}
    assert all(row['sha256']==formal['modules'][name]['sha256'] for name,row in modules.items())
    files={'/'+path:digest for path,digest in proof['installed_files'].items()}
    assert files['/usr/lib/libcamera.so.0.7.2']=='0884c73489815132b5f180c303ab5ed2edc4c52f0f7b191365054aa855849a48'
    return dict(packages=proof['packages'],modules=modules,installed_files=files,
                library_sha256=files['/usr/lib/libcamera.so.0.7.2'],kernel_release=proof['uname'])


def frozen():
    names={451:['capture-body-comparison.py','observe-comparison.py','prepare-comparison.py',
                'check-comparison.py','source-state.json','source-validation.json','build-validation.json',
                'generated-validation.json','arm-wire-validation.json','0062-camss-worker-byte-vector-wire-compatible.patch'],
           452:['capture-body-diagnostic.py','prepare-diagnostic.py','check-diagnostic.py','source-state.json',
                'source-validation.json','source-draft-validation.json','build-validation.json','build-r2-validation.json',
                'full_ownership_trace.h','0063-camss-bounded-full-ownership-trace.patch']}
    current={f'kernel{stage}/{name}':sha(HERE.parent/f'kernel{stage}'/name)
             for stage,items in names.items() for name in items}
    marker=PRIVATE/'immutable-inputs-v2-private.json'
    value=dict(schema='samurai-camera-preflight-immutable-inputs-v2',files=current)
    if marker.exists(): assert json.loads(marker.read_text())==value, 'Frozen 451/452 immutable inputs changed'
    else: marker.write_text(json.dumps(value,indent=2)+'\n')
    assert sha(HERE/'capture-body-comparison.py')==BODY_SHA
    assert sha(HERE/'observe-comparison.py')==OBSERVER_SHA
    builds={stage:json.loads((HERE.parent/f'kernel{stage}/build-validation.json').read_text()) for stage in [451,452]}
    assert all(row['passed'] for row in builds.values())
    assert next(r['sha256'] for r in builds[451]['runtime_files'] if r['name']=='camss_ipa_proxy')=='35526054954ce43d1068c710f6be6d4cd172288e4da7ffcab677712815f08f4d'
    assert next(r['sha256'] for r in builds[452]['runtime_files'] if r['name']=='libcamera.so.0.7.2')=='e6a90a0699fa62a2c00a03a053bd93d8449450757301bbf7b3804978ceb073d6'
    return current


def baseline_code():
    tree=ast.parse((HERE.parent/'kernel441/preflight.py').read_text())
    original=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                  and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
    body=ast.parse(original)
    last=body.body[-1]
    assert isinstance(last,ast.Expr) and isinstance(last.value,ast.Call) and last.value.func.id=='print'
    dumps=last.value.args[0]
    assert isinstance(dumps,ast.Call) and dumps.func.attr=='dumps' and dumps.args[0].func.id=='dict'
    body.body[-1]=ast.Assign(targets=[ast.Name(id='baseline',ctx=ast.Store())],value=dumps.args[0])
    ast.fix_missing_locations(body)
    return ast.unparse(body)+'\n',hashlib.sha256(original.encode()).hexdigest()


def charging_code():
    path=HERE/'capture-body-comparison.py'
    assert sha(path)==BODY_SHA
    text=path.read_text()
    tree=ast.parse(text)
    return '\n\n'.join(ast.get_source_segment(text,n) for n in tree.body
                        if isinstance(n,ast.FunctionDef) and n.name in ['sha','charging'])+'\n'


def render(owner, owner_sha, window, expected, nonce):
    baseline,source_sha=baseline_code()
    source='from pathlib import Path\nimport hashlib,json,os,re,runpy,subprocess,sys\nfrom datetime import datetime,timezone\nsys.dont_write_bytecode=True\n'
    source+='owner='+repr(owner)+'\nexpected='+repr(expected)+'\n'
    source+='assert owner is not None, "Mainline owner-return required before any device query"\n'
    source+='''boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot.decode().strip()==owner['boot_id']
guard=Path(owner['boot_guard_path'])
assert guard.is_file() and guard.read_bytes()==boot
assert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()==owner['charging_manifest_sha256']
assert os.uname().release==expected['kernel_release']
'''
    source+=charging_code()+'charging_before=charging()\n'
    source+=baseline
    source+='''baseline['installed_files']={path:sha(path) for path in expected['installed_files']}
baseline['library_sha256']=sha('/usr/lib/libcamera.so.0.7.2')
baseline['kernel_release']=os.uname().release
baseline['pm']={name:Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip() for name in DEVICES}
baseline['services']={}
for name in ['pipewire','wireplumber']:
 found=[]
 for entry in Path('/proc').glob('[0-9]*'):
  try:
   if (entry/'comm').read_text().strip()!=name:continue
   fields=(entry/'stat').read_text().rsplit(')',1)[1].split()
   if fields[0]=='Z':continue
   values=dict(line.split(':',1) for line in (entry/'status').read_text().splitlines() if ':' in line)
   found.append(dict(pid=int(entry.name),start_ticks=int(fields[19]),uids=[int(v) for v in values['Uid'].split()]))
  except (FileNotFoundError,ProcessLookupError):pass
 baseline['services'][name]=found
for name,row in expected['modules'].items():
 assert Path(subprocess.check_output(['modinfo','-n',name],text=True).strip()).resolve()==Path(row['path']).resolve()
 assert subprocess.check_output(['modinfo','-F','intree',row['path']],text=True).strip()=='Y'
 assert 'test_' not in subprocess.check_output(['modinfo','-F','parm',row['path']],text=True)
charging_after=charging()
assert charging_before==charging_after
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot and guard.read_bytes()==boot
'''.replace('DEVICES',repr(DEVICES))
    source+='print(json.dumps(dict(schema="samurai-camera-preflight-observation-v1",window_id='+repr(window)+',owner_return_sha256='+repr(owner_sha)+',request_id='+repr(nonce)+',observed_at_utc=datetime.now(timezone.utc).isoformat(),baseline=baseline,charging=charging_after)))\n'
    ast.parse(source)
    forbidden={'write_text','write_bytes','mkdir','unlink','symlink_to','chmod','chown','kill','killpg','Popen'}
    assert not any(isinstance(n,ast.Attribute) and n.attr in forbidden for n in ast.walk(ast.parse(source)))
    assert 'new_guard' not in source and "with p.open('x')" not in source
    return source,source_sha


def validate_observation(data, owner, expected, window, owner_sha, nonce):
    assert data['schema']=='samurai-camera-preflight-observation-v1'
    assert data['window_id']==window and data['owner_return_sha256']==owner_sha and data['request_id']==nonce
    baseline=data['baseline']
    assert baseline['boot_id'].strip()==owner['boot_id'] and baseline['taint']==0
    assert baseline['kernel_release']==expected['kernel_release'] and baseline['packages']==expected['packages']
    assert baseline['installed_files']==expected['installed_files'] and baseline['library_sha256']==expected['library_sha256']
    assert set(baseline['modules'])==set(expected['modules'])
    for name,row in expected['modules'].items():
        assert baseline['modules'][name]==dict(sha256=row['sha256'],note=row['note'])
        assert baseline['notes'][name]==row['note']
    status=baseline['status']
    assert status['registered'] and not any(status[k] for k in IDLE)
    assert status['jobs']==status['completed']==status['direct_completed']
    assert not any(baseline['core'][k] for k in RELEASED)
    assert baseline['pm']=={name:'suspended' for name in DEVICES}
    assert set(baseline['services'])=={'pipewire','wireplumber'}
    for rows in baseline['services'].values():
        assert len(rows)==1 and rows[0]['uids']==[10000]*4 and rows[0]['pid']>0 and rows[0]['start_ticks']>0
    charging=data['charging']
    assert set(charging)==CHARGING_KEYS and charging['manifest_sha256']==owner['charging_manifest_sha256']
    assert set(charging['notes'])=={'samurai_usb_input','samurai_gauge_protection','samurai_mp2650'}
    assert all(re.fullmatch(r'[0-9a-f]{64}',v) for v in charging['notes'].values())
    assert set(charging['limits'])=={'input_current_limit','constant_charge_current','constant_charge_voltage'}
    assert all(type(v) is int and v>=0 for v in charging['limits'].values())
    for key in ['service_enabled','native_retained','control_enabled']: assert charging[key] is True
    for key in ['source_budget_ua','native_udc_allowance_ua','gadget_maxpower_ma']: assert type(charging[key]) is int and charging[key]>=0
    assert isinstance(charging['source_type'],str) and charging['source_type']
    if 'charging' in owner: assert owner['charging']==charging


def self_test(expected,source,protected,baseline_sha):
    window='k451-proxy-comparison-r1'
    owner=dict(schema='samurai-camera-owner-return-v1',return_id='synthetic-only',issued_at_utc=stamp(),
               from_owner='charging',to_owner='camera',released=True,original_key_verified=True,
               charging_worker_exited=True,no_concurrent_owner=True,authorized_window_ids=[window],
               boot_id='00000000-0000-0000-0000-000000000001',boot_guard_path=GUARD,
               charging_manifest_sha256='1'*64,provenance_sha256='2'*64)
    validate_owner(owner,window,check_files=False)
    rejected=[]
    def rejects(label,fn):
        try: fn()
        except (AssertionError,KeyError,ValueError,TypeError): rejected.append(label)
        else: raise AssertionError('Counterexample accepted: '+label)
    for key,value in [('released',False),('original_key_verified',False),('charging_worker_exited',False),
                      ('no_concurrent_owner',False),('to_owner','charging'),('boot_guard_path','/tmp/new-guard'),
                      ('issued_at_utc','2000-01-01T00:00:00+00:00'),('authorized_window_ids',['k452-full-diagnostic-r1']),
                      ('boot_id','only-a-prefix')]:
        trial=copy.deepcopy(owner);trial[key]=value
        rejects('owner-'+key,lambda t=trial:validate_owner(t,window,check_files=False))
    charging=dict(manifest_sha256='1'*64,notes={name:'3'*64 for name in ['samurai_usb_input','samurai_gauge_protection','samurai_mp2650']},
                  limits={key:1 for key in ['input_current_limit','constant_charge_current','constant_charge_voltage']},
                  source_type='synthetic',source_budget_ua=1,native_udc_allowance_ua=1,gadget_maxpower_ma=1,
                  service_enabled=True,native_retained=True,control_enabled=True)
    baseline=dict(boot_id=owner['boot_id']+'\n',taint=0,kernel_release=expected['kernel_release'],packages=copy.deepcopy(expected['packages']),
                  modules={name:dict(sha256=row['sha256'],note=row['note']) for name,row in expected['modules'].items()},
                  notes={name:row['note'] for name,row in expected['modules'].items()},installed_files=copy.deepcopy(expected['installed_files']),
                  library_sha256=expected['library_sha256'],status={**{key:0 for key in IDLE},'registered':True,'jobs':0,'completed':0,'direct_completed':0},
                  core={key:0 for key in RELEASED},pm={name:'suspended' for name in DEVICES},
                  services={name:[dict(pid=1,start_ticks=1,uids=[10000]*4)] for name in ['pipewire','wireplumber']})
    sample=dict(schema='samurai-camera-preflight-observation-v1',window_id=window,owner_return_sha256='4'*64,
                request_id='synthetic',baseline=baseline,charging=charging)
    validate_observation(sample,owner,expected,window,'4'*64,'synthetic')
    mutations=[('boot',lambda d:d['baseline'].update(boot_id='other')),
               ('nonce',lambda d:d.update(request_id='replayed')),
               ('owner-digest',lambda d:d.update(owner_return_sha256='0'*64)),
               ('taint',lambda d:d['baseline'].update(taint=1)),
               ('formal-library',lambda d:d['baseline'].update(library_sha256='0'*64)),
               ('formal-package',lambda d:d['baseline']['packages'].update(libcamera='wrong')),
               ('module-file',lambda d:d['baseline']['modules']['qcom_camss'].update(sha256='0'*64)),
               ('loaded-note',lambda d:d['baseline']['notes'].update(qcom_camss='0'*64)),
               ('m2m-active',lambda d:d['baseline']['status'].update(users=1)),
               ('m2m-uncompleted',lambda d:d['baseline']['status'].update(jobs=1)),
               ('core-held',lambda d:d['baseline']['core'].update(mapped_bytes=4096)),
               ('camera-active',lambda d:d['baseline']['pm'].update({'ac10000.icp':'active'})),
               ('service-duplicate',lambda d:d['baseline']['services']['pipewire'].append(dict(pid=2,start_ticks=1,uids=[10000]*4))),
               ('service-root',lambda d:d['baseline']['services']['wireplumber'][0].update(uids=[0]*4)),
               ('charging-manifest',lambda d:d['charging'].update(manifest_sha256='0'*64)),
               ('charging-control',lambda d:d['charging'].update(control_enabled=False)),
               ('charging-incomplete',lambda d:d['charging'].pop('notes'))]
    for label,mutate in mutations:
        trial=copy.deepcopy(sample);mutate(trial)
        rejects(label,lambda t=trial:validate_observation(t,owner,expected,window,'4'*64,'synthetic'))
    # Static query boundary: the only child programs are read-only modinfo queries.
    tree=ast.parse(source)
    commands=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
              and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess']
    assert commands and all(n.func.attr=='check_output' and isinstance(n.args[0],ast.List)
                            and n.args[0].elts[0].value=='modinfo' for n in commands)
    assert protected==frozen()
    report=dict(stage=451,offline_only=True,phone_accessed=False,ssh_called=False,fresh_preflight_verified=False,
                generated_query_python_syntax_passed=True,query_only_uses_modinfo_child_commands=True,
                reused_441_readonly_baseline_sha256=baseline_sha,reused_frozen_451_charging_sha256=BODY_SHA,
                frozen_observer_sha256=OBSERVER_SHA,immutable_fingerprints=protected,
                dynamic_plan_runtime_receipts_and_mainline_staging_excluded=True,
                counterexamples_rejected=rejected,synthetic_inputs_not_hardware_evidence=True,
                existing_guard_read_only=True,owner_charging_snapshot_optional=True,
                mainline_owner_required_before_live=True,stage_launch_phone_writes_absent=True,
                checker_sha256=sha(__file__),passed=True)
    (HERE/'preflight-offline-validation.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--window-id',default='k451-proxy-comparison-r1')
    parser.add_argument('--owner-return',type=Path)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    window_valid(args.window_id)
    spec=importlib.util.spec_from_file_location('preflight_storage449',HERE.parent/'kernel449/storage.py')
    storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
    storage.mount.mounted_build()
    PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    protected=frozen()
    expected=inputs()
    owner=None
    owner_sha='MAINLINE_OWNER_RETURN_REQUIRED'
    if args.owner_return:
        path=local_path(str(args.owner_return))
        owner=json.loads(path.read_bytes())
        validate_owner(owner,args.window_id)
        owner_sha=sha(path)
    assert not args.live or owner is not None, '--live requires a new trusted owner return'
    assert not (args.live and args.self_test)
    work=PRIVATE/args.window_id/(owner['return_id'] if owner else 'pending-owner-return')
    work.mkdir(mode=0o700,parents=True,exist_ok=True)
    nonce=secrets.token_hex(16)
    source,baseline_sha=render(owner,owner_sha,args.window_id,expected,nonce)
    (work/'query-private.py').write_text(source)
    if args.self_test:
        self_test(expected,source,protected,baseline_sha)
    if not args.live:
        print(json.dumps(dict(rendered=True,phone_accessed=False,fresh_preflight_verified=False,
                              window_id=args.window_id,query_private=str(work/'query-private.py'))))
        return
    assert not (work/'handoff-private.json').exists(), 'Never overwrite a prior successful handoff'
    validate_owner(owner,args.window_id)
    # Only now load the established strict-original-key transport, never host.ssh/adoption.
    spec=importlib.util.spec_from_file_location('preflight_transport451',HERE/'host.py')
    host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
    result=host.raw_ssh('python3 -B -c '+shlex.quote(source),timeout=35)
    result.check_returncode()
    data=json.loads(result.stdout)
    validate_observation(data,owner,expected,args.window_id,owner_sha,nonce)
    assert sha(args.owner_return)==owner_sha, 'Owner return changed during preflight'
    validate_owner(owner,args.window_id)
    assert protected==frozen()
    (work/'observation-private.json').write_bytes(result.stdout)
    baseline=work/'baseline-private.json'
    baseline.write_text(json.dumps(data['baseline'],indent=2)+'\n')
    (work/'charging-snapshot-private.json').write_text(json.dumps(data['charging'],indent=2)+'\n')
    handoff=dict(schema='samurai-camera-handoff-v1',window_id=args.window_id,window_owner='camera',
                 fresh_preflight_verified=True,issued_at_utc=stamp(),boot_guard_path=GUARD,
                 formal_baseline_sha256=sha(baseline),formal_library_sha256=expected['library_sha256'],charging=data['charging'])
    (work/'handoff-private.json').write_text(json.dumps(handoff,indent=2)+'\n')
    print(json.dumps(dict(window_id=args.window_id,read_only_preflight_passed=True,phone_changed=False,
                          handoff_private=str(work/'handoff-private.json'),baseline_private=str(baseline))))


if __name__=='__main__':
    main()
