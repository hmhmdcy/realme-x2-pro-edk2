"""Narrow rollback adapter to the existing R2 owner; default never connects."""
from pathlib import Path
import argparse, base64, json, os, re, secrets, sys
if sys.flags.optimize: raise RuntimeError('nonoptimized Python required')
sys.dont_write_bytecode = True
import sources, proof
HERE = Path(__file__).resolve().parent
PRIVATE = sources.local('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-rollback-activation')
_OWNER = None

def owner():
    global _OWNER
    if _OWNER is None:
        sources.source_check()
        module = sources.load('activation_controller')
        # The exact existing scheduling methods continue to own every child.
        # Their process entry and immutable source SHA now name this adapter.
        module.__file__ = str(Path(__file__).resolve()); module.HERE = HERE
        module.WORKERS = HERE; module.PRIVATE = PRIVATE; module.TX_PATTERN = proof.TX_PATTERN
        module.WORKER_HASHES = sources.worker_hashes(); module.source_check = sources.controller_pins
        module.bound = bound; module.export_context = export_context
        _OWNER = module
    return _OWNER

def probe_payload(rollback_directory, rollback_fetch_directory):
    review = proof.review_completed(rollback_directory, rollback_fetch_directory)
    request = proof.post_probe_request(review['request'], review['result_sha256'], review['host_binding_sha256'])
    path = sources.local(sources.pins()['baseline']['current_probe']['path'])
    return ('PROBE_REQUEST=' + repr(request) + '\n').encode() + path.read_bytes()

def bind(transaction, rollback_directory, rollback_fetch_directory, probe_directory, *, private=PRIVATE):
    sources.source_check()
    # Real rollback and post-restore original-key evidence precede all mkdirs.
    reviewed = proof.review_completed(rollback_directory, rollback_fetch_directory, probe_directory)
    token = secrets.token_hex(24); guard = proof.make_guard(transaction, token, reviewed)
    root = Path(private); directory = root / transaction
    sources.need(not directory.exists() and not (root / 'active-owner-private.json').exists(), 'new independent owner/directory')
    base = owner(); hashes = sources.worker_hashes()
    files = {name:(HERE/name).read_bytes() for name in hashes}
    files.update({'common.py':(HERE/'common.py').read_bytes(), 'proof.py':(HERE/'proof.py').read_bytes(),
                  'activation-supervisor.py':(HERE/'supervisor.py').read_bytes(),
                  'camera481-expected-private.json':sources.local(sources.pins()['baseline']['camera_wrapper']['path']).read_bytes()})
    guard_raw = proof.encode(guard)
    request = dict(schema='samurai-usb-irq-protection-host-request-v1', transaction_id=transaction, token=token,
        expected_boot=guard['boot_id'], guard_sha256=sources.sha(guard_raw),
        files={name:dict(sha256=sources.sha(raw),base64=base64.b64encode(raw).decode()) for name,raw in files.items()},
        guard_base64=base64.b64encode(guard_raw).decode(), worker_hashes=hashes,
        common_sha256=sources.sha(files['common.py']), supervisor_sha256=sources.sha(files['activation-supervisor.py']))
    binding = dict(schema='samurai-irq-rollback-restart-host-binding-v1', transaction_id=transaction,
        rollback_directory=str(sources.local(rollback_directory).resolve()),
        rollback_fetch_directory=str(sources.local(rollback_fetch_directory).resolve()),
        post_restore_probe_directory=str(sources.local(probe_directory).resolve()), review=reviewed,
        endpoint=dict(kind='usb-ipv6',peer=proof.PEER,host_key_alias='169.254.42.1',original_key_verified=True,
                      observed_new_boot=guard['boot_id']),
        source_pins_sha256=sources.sha((HERE/'source-pins.json').read_bytes()), guard_sha256=sources.sha(guard_raw),
        request_sha256=sources.sha(proof.encode(request)), device_accessed=False)
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    base.save(root/'active-owner-private.json',dict(transaction_id=transaction,token=token,boot_id=guard['boot_id']))
    directory.mkdir(mode=0o700)
    base.create(directory/'guard-private.json',guard_raw);base.save(directory/'request-private.json',request)
    base.save(directory/'binding-private.json',binding)
    return dict(bound=True,directory=str(directory),runtime_validation_accepted=False,device_accessed=False)

def bound(transaction, *, private=PRIVATE, revalidate=False):
    sources.need(re.fullmatch(proof.TX_PATTERN,transaction), 'rollback activation name')
    sources.source_check(); base=owner();directory=Path(private)/transaction
    binding=base.load_json(directory/'binding-private.json');request_raw=(directory/'request-private.json').read_bytes()
    request=json.loads(request_raw);guard_raw=(directory/'guard-private.json').read_bytes();guard=json.loads(guard_raw)
    sources.need(binding['transaction_id']==request['transaction_id']==guard['transaction_id']==transaction and
        binding['source_pins_sha256']==sources.sha((HERE/'source-pins.json').read_bytes()) and
        binding['request_sha256']==sources.sha(request_raw) and
        binding['guard_sha256']==request['guard_sha256']==sources.sha(guard_raw) and
        base64.b64decode(request['guard_base64'],validate=True)==guard_raw,'immutable rollback restart inputs')
    sources.need(base.load_json(Path(private)/'active-owner-private.json')==dict(transaction_id=transaction,token=request['token'],boot_id=request['expected_boot']), 'existing exact owner')
    if revalidate:
        review=proof.review_completed(binding['rollback_directory'],binding['rollback_fetch_directory'],binding['post_restore_probe_directory'])
        sources.need(review==binding['review'] and proof.make_guard(transaction,request['token'],review)==guard,'original successful rollback/probe changed')
    return directory,request,binding,sources.controller_pins()

def export_context(directory):
    base=owner();directory=Path(directory);guard=base.load_json(directory/'guard-private.json');binding=base.load_json(directory/'binding-private.json')
    sources.need((directory/'quiesce-process-private.json').exists(),'actual qualified quiesce required')
    claim=base.load_json(directory/'restart-claim-private.json');selection=base.load_json(directory/'restart-job-private.json')
    terminal,_=base.terminal_job(selection['job'])
    sources.need(all(claim[k]==guard[k] for k in ('transaction_id','token','boot_id')),'bound restart claim')
    dispatch=dict(schema='samurai-eud-restart-dispatch-v1',transaction_id=guard['transaction_id'],token=guard['token'],boot_id=guard['boot_id'],
        guard_sha256=sources.sha((directory/'guard-private.json').read_bytes()),request_count=1,state='dispatched_once',
        worker_sha256=sources.worker_hashes()['eud-restart.py'],argv=claim['argv'],host_process=terminal,
        host_claim_sha256=sources.sha((directory/'restart-claim-private.json').read_bytes()),
        restart_claim_intent='claimed_by_pinned_worker',restart_claim_observed=False,syscall_success_proven=False)
    target=directory/'restart-dispatch-private.json'
    if target.exists(): sources.need(base.load_json(target)==dispatch,'original dispatch changed')
    else: base.save(target,dispatch)
    files={key:base.fact(directory/name) for key,name in {
        'guard':'guard-private.json','quiesce_state':'quiesce-state-private.json','quiesce_summary':'quiesce-summary-private.json',
        'quiesce_boot_id':'quiesce-boot-id-private.txt','quiesce_process':'quiesce-process-private.json',
        'restart_dispatch':'restart-dispatch-private.json','restart_claim':'restart-claim-private.json'}.items()}
    context=dict(schema='samurai-usb-irq-protection-rollback-fastboot-context-v1',transaction_id=guard['transaction_id'],token=guard['token'],
        old_boot_id=guard['boot_id'],guard_sha256=files['guard']['sha256'],files=files,
        rollback_directory=binding['rollback_directory'],rollback_fetch_directory=binding['rollback_fetch_directory'],
        post_restore_probe_directory=binding['post_restore_probe_directory'])
    base.save(directory/'host-context-private.json',context);return context

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',nargs='?',default='check-local',choices=['check-local','bind','prepare','quiesce','status','fetch','inspect','restart','_ssh-worker'])
    parser.add_argument('--transaction');parser.add_argument('--rollback-directory');parser.add_argument('--rollback-fetch-directory')
    parser.add_argument('--post-restore-probe-directory');parser.add_argument('--job')
    parser.add_argument('--execute',action='store_true');parser.add_argument('--window-confirmed',action='store_true');args=parser.parse_args()
    if args.action=='check-local':
        sources.source_check();print(json.dumps(dict(source_only=True,runtime_material_created=False,device_accessed=False)));return 0
    if args.action=='_ssh-worker':owner().ssh_worker(args.job);return 0
    if args.action=='bind':value=bind(args.transaction,args.rollback_directory,args.rollback_fetch_directory,args.post_restore_probe_directory)
    else:value=owner().run(args.action,args.transaction,args.execute,args.window_confirmed)
    print(json.dumps(value,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
