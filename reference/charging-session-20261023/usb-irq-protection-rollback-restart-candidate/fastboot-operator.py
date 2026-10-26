"""Existing boot-only owner with rollback-context validation; explicit actions only."""
from pathlib import Path
import json, re, sys
if sys.flags.optimize: raise RuntimeError('nonoptimized Python required')
sys.dont_write_bytecode = True
import sources, proof
HERE = Path(__file__).resolve().parent
_OWNER = None

def pinned_tools():
    sources.source_check(); pins=sources.pins()['local']
    return {'prepare-contract.json':pins['prepare-contract.json']['sha256'],
            'eud-restart.py':pins['eud-restart.py']['sha256']}

def owner():
    global _OWNER
    if _OWNER is None:
        sources.source_check(); module=sources.load('fastboot_operator')
        frozen_source_inputs=module.source_inputs
        def inputs():
            sources.source_check();return frozen_source_inputs()
        module.source_inputs=inputs;module.pinned_tools=pinned_tools
        module.__file__=str(Path(__file__).resolve());module.validate_context=validate_context
        # Preserve the original command, once, process and terminal code. The
        # candidate flash direction is absent from this rollback-only adapter.
        module.IMAGES={'original':module.IMAGES['original']}
        module.PAIR_ACTIONS={'rollback-original':'original'}
        module.REBOOT_IMAGES={'reboot-original':('rollback-original','original')}
        module.ACTIONS=('inspect','rollback-original','reboot-original')
        _OWNER=module
    return _OWNER

def validate_context(path, contract=None):
    base=owner();require=base.require;read_json=base.read_json;reference_file=base.reference_file
    path=Path(path)
    require(path.name=='host-context-private.json' and path.is_file() and not path.is_symlink(),'regular context filename')
    path=path.resolve();context=read_json(path)
    require(context['schema']=='samurai-usb-irq-protection-rollback-fastboot-context-v1','rollback context schema')
    txn,token,boot=(context[k] for k in ('transaction_id','token','old_boot_id'))
    require(re.fullmatch(proof.TX_PATTERN,txn) and re.fullmatch('[0-9a-f]{48}',token) and
            re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',boot),'rollback restart identity')
    require(path.parent.name==txn,'new restart directory')
    keys={'guard','quiesce_state','quiesce_summary','quiesce_boot_id','quiesce_process','restart_dispatch','restart_claim'}
    require(set(context['files'])==keys,'exact original seven-file context')
    paths={k:reference_file(path.parent,v) for k,v in context['files'].items()}
    require(len(set(paths.values()))==len(keys) and context['guard_sha256']==context['files']['guard']['sha256'],'distinct bound raw files')
    guard=read_json(paths['guard'])
    require((guard['transaction_id'],guard['token'],guard['boot_id'])==(txn,token,boot),'guard identity')
    sources.source_check()
    review=proof.review_completed(context['rollback_directory'],context['rollback_fetch_directory'],context['post_restore_probe_directory'])
    require(guard==proof.make_guard(txn,token,review),'original successful rollback and post-restore probe differ')
    expected=read_json(HERE/'prepare-contract.json')
    require(contract is None or contract==expected,'pinned rollback contract')
    require(expected['context_schema']==context['schema'] and expected['operator_actions']==list(base.ACTIONS),'rollback-only contract')
    for name in ('quiesce_state', 'quiesce_summary', 'quiesce_process', 'restart_claim', 'restart_dispatch'):
        item = read_json(paths[name])
        require((item['transaction_id'], item['token'], item['boot_id']) == (txn, token, boot), name + ' identity differs')
    state, summary, process = (read_json(paths[k]) for k in ('quiesce_state', 'quiesce_summary', 'quiesce_process'))
    require(state['terminal'] is True and type(state['exit_code']) is int and state['exit_code'] == 0
            and summary['taint'] == 0, 'quiesce did not successfully terminate')
    require(paths['quiesce_boot_id'].read_text().strip() == boot, 'retained quiesce boot differs')
    remote = '/root/charging-management-20261023/' + txn
    qargv = ['python3', '-B', remote + '/eud-quiesce.py', '--guard', remote + '/guard-private.json', '--commit-quiesce']
    require(process['pid'] == state['pid'] and type(process['pid']) is int and process['pid'] > 0
            and type(process['startticks']) is int and process['startticks'] > 0
            and process['argv'] == qargv and process['status'] in ('absent', 'zombie'), 'original quiesce process not ended')
    rargv = ['python3', '-B', remote + '/eud-restart.py', '--guard', remote + '/guard-private.json', '--commit-restart2-bootloader']
    claim, dispatch = (read_json(paths[k]) for k in ('restart_claim', 'restart_dispatch'))
    require(claim['schema'] == 'samurai-eud-restart-host-claim-v1'
            and dispatch['schema'] == 'samurai-eud-restart-dispatch-v1', 'restart receipt schema')
    for item in (claim, dispatch):
        require(item['guard_sha256'] == context['guard_sha256'] and type(item['request_count']) is int
                and item['request_count'] == 1 and item['worker_sha256'] == pinned_tools()['eud-restart.py']
                and item['argv'] == rargv, 'original restart source or claim differs')
    child = dispatch['host_process']
    require(dispatch['host_claim_sha256'] == context['files']['restart_claim']['sha256']
            and dispatch['state'] == 'dispatched_once' and dispatch['restart_claim_intent'] == 'claimed_by_pinned_worker'
            and type(child['pid']) is int and child['pid'] > 0 and type(child['startticks']) is int and child['startticks'] > 0
            and child['argv'] and child['terminal'] is True and type(child['returncode']) is int,
            'original restart transport not terminal or bound')
    return context

def main():
    if len(sys.argv)==3 and sys.argv[1]=='--_worker':
        owner().worker(sys.argv[2]);return 0
    if not sys.argv[1:] or sys.argv[1:] in (['--check-local'], ['check-local']):
        sources.source_check();owner().source_inputs()
        print(json.dumps(dict(source_only=True,runtime_material_created=False,device_accessed=False)))
        return 0
    return owner().main()

if __name__=='__main__':raise SystemExit(main())
