"""Render/inspect a new-boot camera preflight; no SSH or device-write entry point."""
from pathlib import Path
import argparse,ast,copy,hashlib,importlib.util,json,re,secrets,sys,uuid
from datetime import datetime,timezone,timedelta

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel461/preflight')
LEGACY_SHA='8f7e01cbabda666a5b1e4897ccef4480564aa76a9514103070a7326caadcd6ab'
# The existing mirror differs only in one unused self-test's synthetic UUID;
# its operational definitions are byte-identical. Keep both exact file pins.
LEGACY_MIRROR_SHA='63bde7c7088f018746a0da0bf1f20b7938c665d02d1236a500b0c1564bc04c95'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def window_valid(value):
    assert re.fullmatch(r'k461-completion-r([1-9]|1[0-9]|20)',value),'Unsupported new camera window'

def load_legacy():
    path=HERE.parent/'kernel451/preflight-handoff.py'
    assert sha(path) in {LEGACY_SHA,LEGACY_MIRROR_SHA},'Review changed baseline renderer before reuse'
    spec=importlib.util.spec_from_file_location('preflight451_for461',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.window_valid=window_valid
    return module

def bind_adoption(legacy,adoption):
    assert adoption['original_key_verified'] is True and adoption['baseline440_verified'] is True
    assert re.fullmatch(r'[0-9a-f]{64}',adoption['charging_manifest_sha256'])
    guard=adoption['guard_path']
    assert re.fullmatch(r'/var/lib/samurai/[A-Za-z0-9_.-]+/boot-id-private\.txt',guard)
    assert guard!='/var/lib/samurai/k449-adopted/boot-id-private.txt','Historical boot guard cannot authorize this window'
    legacy.GUARD=guard

def validate_owner(legacy,owner,adoption,window,check_files=True):
    bind_adoption(legacy,adoption)
    legacy.validate_owner(owner,window,check_files=check_files)
    assert owner['charging_manifest_sha256']==adoption['charging_manifest_sha256']

def render(legacy,owner,adoption,window,expected,owner_sha,nonce):
    window_valid(window)
    bind_adoption(legacy,adoption)
    source,baseline_sha=legacy.render(owner,owner_sha,window,expected,nonce)
    # The reused query checks the supplied existing guard before its first device inventory.
    assert 'guard.read_bytes()==boot' in source
    ast.parse(source)
    return source,baseline_sha

def self_test():
    legacy=load_legacy();window='k461-completion-r1'
    adoption=dict(original_key_verified=True,baseline440_verified=True,
                  guard_path='/var/lib/samurai/charging-r7-model-adopted/boot-id-private.txt',
                  charging_manifest_sha256='1'*64)
    owner=dict(schema='samurai-camera-owner-return-v1',from_owner='charging',to_owner='camera',
               released=True,original_key_verified=True,charging_worker_exited=True,no_concurrent_owner=True,
               return_id='host-model',authorized_window_ids=[window],
               issued_at_utc=datetime.now(timezone.utc).isoformat(),boot_id=str(uuid.UUID(int=1)),
               boot_guard_path=adoption['guard_path'],charging_manifest_sha256='1'*64,provenance_sha256='2'*64)
    validate_owner(legacy,owner,adoption,window,check_files=False)
    cases=[]
    def rejects(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError):cases.append(name)
        else:raise AssertionError('Accepted '+name)
    for name,key,value in [('old-guard','boot_guard_path','/var/lib/samurai/k449-adopted/boot-id-private.txt'),
                           ('manifest-mismatch','charging_manifest_sha256','3'*64),
                           ('owner-still-active','released',False),('concurrent-owner','no_concurrent_owner',False),
                           ('stale-owner','issued_at_utc',(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()),
                           ('old-window','authorized_window_ids',['k452-full-diagnostic-r2']),
                           ('boot-prefix','boot_id','not-a-full-uuid')]:
        trial=copy.deepcopy(owner);trial[key]=value
        rejects(name,lambda t=trial:validate_owner(legacy,t,adoption,window,check_files=False))
    old=copy.deepcopy(adoption);old['guard_path']='/var/lib/samurai/k449-adopted/boot-id-private.txt'
    rejects('old-adoption',lambda:bind_adoption(legacy,old))
    source,_=render(legacy,None,adoption,window,{},'MISSING','host-model')
    try:exec(compile(source,'unbound-preflight','exec'),{})
    except AssertionError as error:assert str(error)=='Mainline owner-return required before any device query'
    else:raise AssertionError('Unbound query executed')
    report=dict(stage=461,legacy_renderer_sha256=LEGACY_SHA,legacy_mirror_sha256=LEGACY_MIRROR_SHA,
                allowed_legacy_variant_only_changes_unused_synthetic_uuid=True,new_guard_model_accepted=True,
                rejected_cases=cases,unbound_query_rejected_before_device_query=True,
                phone_accessed=False,fresh_hardware_preflight_proven=False,passed=True)
    (HERE/'preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--window-id',default='k461-completion-r1')
    parser.add_argument('--adoption',type=Path,default=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/boot-adoption-private.json'))
    parser.add_argument('--owner-return',type=Path)
    parser.add_argument('--request',type=Path,help='Inspect a previously rendered request with --observation')
    parser.add_argument('--observation',type=Path)
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:self_test();return
    legacy=load_legacy();window_valid(args.window_id)
    adoption_path=legacy.local_path(str(args.adoption));adoption=json.loads(adoption_path.read_bytes())
    bind_adoption(legacy,adoption)
    expected=legacy.inputs()
    owner=None;owner_sha='MAINLINE_OWNER_RETURN_REQUIRED'
    if args.owner_return:
        owner_path=legacy.local_path(str(args.owner_return));owner=json.loads(owner_path.read_bytes())
        validate_owner(legacy,owner,adoption,args.window_id);owner_sha=sha(owner_path)
    assert bool(args.request)==bool(args.observation),'Inspect requires both request and observation'
    if args.request:
        assert owner is not None
        request_path=legacy.local_path(str(args.request));request=json.loads(request_path.read_bytes())
        assert request_path.parent.resolve().is_relative_to(PRIVATE.resolve())
        work=request_path.parent
        assert request['window_id']==args.window_id and request['owner_return_sha256']==owner_sha
        assert request['adoption_sha256']==sha(adoption_path) and request['expected']==expected
        assert sha(work/'query-private.py')==request['query_sha256'] and request['bound'] is True
        observation_path=legacy.local_path(str(args.observation));data=json.loads(observation_path.read_bytes())
        observed=datetime.fromisoformat(data['observed_at_utc'].replace('Z','+00:00'))
        assert observed.tzinfo is not None and 0<=(legacy.utc()-observed).total_seconds()<=600
        legacy.validate_observation(data,owner,expected,args.window_id,owner_sha,request['nonce'])
        validate_owner(legacy,owner,adoption,args.window_id)
        assert not (work/'handoff-private.json').exists(),'Never overwrite a successful handoff'
        baseline=work/'baseline-private.json';baseline.write_text(json.dumps(data['baseline'],indent=2)+'\n')
        handoff=dict(schema='samurai-camera-handoff-v1',window_id=args.window_id,window_owner='camera',
                     fresh_preflight_verified=True,issued_at_utc=legacy.stamp(),boot_guard_path=adoption['guard_path'],
                     formal_baseline_sha256=sha(baseline),formal_library_sha256=expected['library_sha256'],charging=data['charging'])
        (work/'handoff-private.json').write_text(json.dumps(handoff,indent=2)+'\n')
        print(json.dumps(dict(inspected=True,phone_accessed_by_this_tool=False,fresh_preflight_verified=True,
                              handoff_private=str(work/'handoff-private.json'))));return
    nonce=secrets.token_hex(16)
    work=PRIVATE/args.window_id/nonce;work.mkdir(mode=0o700,parents=True,exist_ok=False)
    source,baseline_sha=render(legacy,owner,adoption,args.window_id,expected,owner_sha,nonce)
    (work/'query-private.py').write_text(source)
    request=dict(window_id=args.window_id,owner_return_sha256=owner_sha,adoption_sha256=sha(adoption_path),
                 nonce=nonce,expected=expected,bound=owner is not None,query_sha256=sha(work/'query-private.py'),
                 baseline_source_sha256=baseline_sha)
    (work/'request-private.json').write_text(json.dumps(request,indent=2)+'\n')
    print(json.dumps(dict(rendered=True,bound=owner is not None,phone_accessed=False,query_private=str(work/'query-private.py'),
                          request_private=str(work/'request-private.json'))))

if __name__=='__main__':main()
