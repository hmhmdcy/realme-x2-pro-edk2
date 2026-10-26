"""Audit cached480 originals only; no transport, SDK, APK invocation or target action."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
# This filename is the requested audit entry point, not Python's stdlib inspect.
sys.path = [item for item in sys.path if Path(item or '.').resolve() != HERE]
import argparse, hashlib, json, re, tarfile
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', type=Path, default=Path('/mnt/e/edk2-samurai-out/kernel480'))
    parser.add_argument('--output', type=Path, default=HERE/'runtime-validation.json')
    args = parser.parse_args(); private = args.private_root
    collected = private/'runtime-collected-r1'; bound = private/'k480-target-deps-r1-bound'
    archive = private/'collect-stdout-private.tar.gz'
    assert archive.stat().st_size == 6700 and sha(archive) == 'b21369df38feba39d9a992dea67bd536d4cb67217f137efb98bf6919d0c1eea7'
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        assert len(members) == 19 and len({m.name for m in members}) == 19
        assert {m.name for m in members} == {p.name for p in collected.iterdir()}
        for member in members:
            assert member.isfile() and Path(member.name).name == member.name
            assert tar.extractfile(member).read() == (collected/member.name).read_bytes()
    plan = load(collected/'plan-private.json'); prepared = load(bound/'preparation-private.json')
    assert (collected/'plan-private.json').read_bytes() == (bound/'plan-private.json').read_bytes()
    assert plan['deployable'] and plan['window_id'] == 'k480-target-deps-r1' and plan['stage'] == 480
    for name, digest in prepared['query_sha256'].items(): assert sha(bound/(name+'-query.py')) == digest
    for name, digest in prepared['source_sha256'].items(): assert sha(HERE/name) == digest
    candidate_path = HERE.parent/'kernel475/candidate-state.json'; candidate = load(candidate_path)
    assert sha(candidate_path) == plan['candidate_state_sha256']
    report_path = HERE.parent/'kernel475/package-r1-validation.json'
    archive_receipt = HERE.parent/'kernel475/private-archive-r2-validation.json'
    for path in [report_path, archive_receipt]:
        assert sha(path) == candidate['public_files_sha256'][path.name] == plan['bound_receipts_sha256'][path.name]
    manifest_path = private.parent/'kernel475/cohort-r2-manifest-private.json'
    assert sha(manifest_path) == load(archive_receipt)['revised_manifest_sha256'] == plan['cohort_manifest_sha256']
    manifest = load(manifest_path); packages = load(report_path)['packages']
    assert plan['packages'] == [{k:p[k] for k in ['name','version','file','bytes','sha256']} for p in packages]
    wanted = {'repository/'+p['file']:p['sha256'] for p in packages}
    wanted['repository/packages.adb'] = manifest['files_sha256']['forward/repository/packages.adb']
    wanted['worker.py'] = sha(HERE/'target-worker.py')
    assert wanted == plan['payload_sha256']
    assert sha(bound/'payload-private.tar.gz') == prepared['bundle_sha256']
    with tarfile.open(bound/'payload-private.tar.gz') as tar:
        for member in tar.getmembers():
            if member.isfile():
                digest = hashlib.sha256(tar.extractfile(member).read()).hexdigest()
                assert digest == (sha(collected/'plan-private.json') if member.name == 'plan-private.json' else wanted[member.name])
    staged = load(collected/'staged-private.json')
    assert staged['passed'] and staged['files_sha256'] == dict(wanted, **{'plan-private.json':sha(collected/'plan-private.json')})
    root = '/var/lib/samurai/k480-target-deps-r1'
    assert (collected/'repositories-private.list').read_text() == 'ndx file://'+root+'/repository/packages.adb\n'
    pins = sorted(p['name']+'='+p['version'] for p in packages); assert pins == plan['pins'] and len(pins) == 7
    common = ['/sbin/apk','--no-network','--repositories-file',root+'/repositories-private.list',
              '--cache-dir',root+'/cache','--logfile=no','--progress=no','--interactive=no']
    verify_files = [root+'/repository/packages.adb']+[root+'/repository/'+p['file'] for p in packages]
    expected_commands = [['/sbin/apk','--version'], common+['verify']+verify_files,
                         common+['add','--simulate','--scripts=no','--commit-hooks=no']+pins]
    state = load(collected/'state-private.json')
    assert len(state['commands']) == 3
    for label, expected, row in zip(['version','verify','simulate'], expected_commands, state['commands']):
        assert row['argv'] == expected and row['exit_code'] == 0
        assert load(collected/(label+'-result-private.json')) == row
        for kind in ['stdout','stderr']:
            assert sha(collected/(label+'-'+kind+'-private.txt')) == row[kind+'_sha256']
        assert (collected/(label+'-stderr-private.txt')).stat().st_size == 0
    assert (collected/'version-stdout-private.txt').read_text() == 'apk-tools 3.0.8-r0, compiled for aarch64.\n'
    assert (collected/'verify-stdout-private.txt').read_text().splitlines() == [p+': OK' for p in verify_files]
    simulated = (collected/'simulate-stdout-private.txt').read_text().splitlines()
    assert len(simulated) == 8 and simulated[-1] == 'OK: 1585.8 MiB in 961 packages'
    expected_upgrades = {p['name']:('99990.7.2-r32' if p['name'].startswith('libcamera') else '0.1.0-r27', p['version']) for p in packages}
    actual_upgrades = {}
    for number, line in enumerate(simulated[:7], 1):
        match = re.fullmatch(r'\((\d+)/7\) Upgrading (\S+) \((\S+) -> (\S+)\)', line)
        assert match and int(match[1]) == number and match[2] not in actual_upgrades
        actual_upgrades[match[2]] = (match[3], match[4])
    assert actual_upgrades == expected_upgrades
    before_path, after_path = [collected/('apk-'+name+'-private.json') for name in ['before','after']]
    assert before_path.read_bytes() == after_path.read_bytes()
    inventory = load(before_path)
    for key in ['/lib/apk/db/installed','/etc/apk/world','/etc/apk/repositories','/etc/apk/keys','/usr/share/apk/keys','/var/log/apk.log']:
        assert key in inventory
    assert all(inventory[key]['type'] == 'file' for key in ['/lib/apk/db/installed','/etc/apk/world'])
    assert state['terminal'] and state['passed'] and state['signature_verification_passed'] and state['solver_passed']
    assert state['global_apk_inventory_byte_identical'] and state['package_transaction_performed'] is False
    launch = load(collected/'launch-private.json'); observed = load(private/'observe-stdout-private.json')
    assert launch == load(private/'launch-stdout-private.json') == observed['launch']
    assert launch == dict(pid=24107, start_ticks='1639532', launched=True)
    assert state['pid'] == launch['pid'] and observed['worker_live'] is False and observed['process_state'] is None
    assert observed['state'] == state
    for name in ['worker-stdout-private.txt','worker-stderr-private.txt','worker-once-private']:
        assert (collected/name).stat().st_size == 0
    health_path = private/'final-health-r1-private.json'; health = load(health_path)
    summary, observation = health['health_audit'], health['health']
    assert summary['passed'] and summary['sample_count'] == 2 and summary['same_boot']
    assert summary['taint'] == 0 and not any(summary['fault_delta'].values())
    assert summary['limits_unchanged'] and summary['camera_and_four_services_unchanged']
    assert observation['installed_files_and_loaded_notes_verified'] and len(observation['samples']) == 2
    for key in ['external_worker_exit_verified','formal_notes_verified','actual_restored_uid10000_services_verified','user_directory_absent']:
        assert health[key] is True
    assert health['trace_used'] is False and (private/'final-health-r1-stderr-private.txt').stat().st_size == 0
    result = dict(stage=480, passed=True, scope='cached-original audit of target trust verification and dependency simulation only',
        actual_apk_version='3.0.8-r0 aarch64', signed_repository_files_verified=8, exact_pinned_packages=7,
        only_seven_planned_upgrades=actual_upgrades, actual_command_exit_codes=[r['exit_code'] for r in state['commands']],
        original_target_trust_used=True, keys_override_or_untrusted_or_force_flags_used=False,
        private_repository_and_cache=True, network_scripts_hooks_and_global_log_disabled=True,
        candidate_state_sha256=sha(candidate_path), bound_plan_sha256=sha(collected/'plan-private.json'),
        worker_sha256=wanted['worker.py'], all_payload_bytes_match475_and_bound_worker=True,
        global_inventory_entries=len(inventory), global_inventory_raw_bytes_identical=True,
        global_inventory_sha256=sha(before_path), installed_db_sha256=inventory['/lib/apk/db/installed']['sha256'],
        world_sha256=inventory['/etc/apk/world']['sha256'],
        original_trust_entries=sum(k.startswith(('/etc/apk/keys/','/usr/share/apk/keys/')) for k in inventory),
        worker=dict(launch, terminal=True, no_live_process_in_external_observe=True, empty_worker_stderr=True),
        external_health=dict(passed=True,sample_count=2,duration_seconds=summary['duration_seconds'],same_boot=True,
            taint=0,fault_delta=summary['fault_delta'],limits_and_services_unchanged=True),
        package_transaction_performed=False, actual_install_upgrade_or_rollback_verified=False,
        default_path_camera_capture_verified=False, phone_accessed_by_inspector=False,sdk_accessed=False,
        collected_archive_bytes=6700,collected_archive_sha256=sha(archive),collected_archive_members=19,
        original_files_sha256={p.name:sha(p) for p in sorted(collected.iterdir())},
        external_evidence_sha256={p.name:sha(p) for p in [private/'observe-stdout-private.json',health_path,private/'final-health-r1-query-private.py']},
        original_preparation_receipt_retained_sha256=sha(HERE/'preparation-validation.json'), inspector_sha256=sha(Path(__file__)))
    assert not args.output.exists(), 'Preserve existing audit; select a new --output if needed'
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['stage','passed','global_inventory_entries','original_trust_entries','collected_archive_sha256']}))


if __name__ == '__main__': main()
