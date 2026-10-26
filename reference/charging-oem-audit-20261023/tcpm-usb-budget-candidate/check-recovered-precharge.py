"""Accept a finished original observation only on its verified later boot."""

REQUIRED_FILES = frozenset(['worker.py', 'exercise.py', 'supervisor.py', 'cpu-load.py',
    'result-private.json', 'worker-terminal.json', 'cpu-load-terminal.json',
    'samples-private.jsonl'])


def check_recovered_precharge(proof, observed):
    def require(condition, reason):
        if not condition:
            raise ValueError(reason)

    prior = proof['original_boot']
    current = proof['recovery_boot']
    require(isinstance(prior, str) and len(prior) == 36 and
            isinstance(current, str) and len(current) == 36 and prior != current,
            'requires a different verified recovery boot')
    require(observed['boot'] == current and observed['guard_boot'] == current,
            'recovery boot or guard changed')
    require(proof['original_records_audited'] is True and proof['actual_records'] == 1299,
            'requires the original complete record audit')
    require(set(proof['file_sha256']) == REQUIRED_FILES and
            observed['file_sha256'] == proof['file_sha256'], 'original evidence changed')
    require(observed['active_original_processes'] == [], 'original observation still active')
    result = observed['result']
    require(all(result[k] is True for k in ['passed', 'stop_confirmed', 'auto_restored',
            'precharge_seen', 'constant_current_seen']), 'original observation did not pass')
    require(result['error'] is None and result['cleanup_error'] is None,
            'original observation or cleanup failed')
    worker = observed['worker_terminal']
    require(type(worker['returncode']) is int and worker['returncode'] == 0 and
            worker['observation_passed'] is True, 'original worker did not finish successfully')
    cpus = observed['cpu_terminal']
    require(cpus['all_joined'] is True and len(cpus['parts']) == 3 and
            {r['pid'] for r in cpus['parts']} == {7505, 7506, 7507} and
            all(r['joined'] is True and type(r['returncode']) is int and
                r['returncode'] == 0 for r in cpus['parts']), 'original load was not joined')
    require(observed['behaviour'] == 'auto' and observed['service_lock_free'] is True,
            'current charging owner is not available in AUTO')
    return dict(original_boot_ended=True, original_worker_passed=True,
                original_load_joined=True, archived_evidence_unchanged=True,
                supervisor_terminal_fabricated=False)
