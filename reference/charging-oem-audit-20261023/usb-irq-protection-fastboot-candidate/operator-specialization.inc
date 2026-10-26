def pinned_tools():
    pins = source_inputs()
    return {'prepare-contract.json': pins['restart/prepare-contract.json'],
            'eud-restart.py': pins['restart/eud-restart.py']}


def source_inputs():
    pins = read_json(HERE / 'source-pins.json')
    require(pins['schema'] == 'samurai-usb-irq-protection-fastboot-source-pins-v1', 'source pin schema')
    require(set(pins['files']) == {'baseline/operator.py', 'boot/delivery.json', 'boot/result.json',
            'cohort/delivery.json', 'restart/delivery.json', 'restart/prepare-contract.json',
            'restart/eud-quiesce.py', 'restart/eud-restart.py', 'stage-proof.py'}, 'source pin set')
    locations = {
        'baseline/operator.py': REF / 'charging-oem-audit-20261023/image502-logdump-activation-candidate/fastboot-operator.py',
        'boot/delivery.json': REF / 'charging-ui-audit-20261023/usb-input-irq-boot-candidate/delivery.json',
        'boot/result.json': REF / 'charging-ui-audit-20261023/usb-input-irq-boot-candidate/result.json',
        'cohort/delivery.json': REF / 'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/delivery.json',
        'restart/delivery.json': RESTART / 'delivery.json',
        'restart/prepare-contract.json': RESTART / 'prepare-contract.json',
        'restart/eud-quiesce.py': RESTART / 'eud-quiesce.py',
        'restart/eud-restart.py': RESTART / 'eud-restart.py',
        'stage-proof.py': STAGE_PROOF,
    }
    for name, path in locations.items():
        require(sha(path) == pins['files'][name], 'frozen source differs: ' + name)
    require(pins['files']['baseline/operator.py'] == '7f473d8698e2e2f83ff768db98de167998a6d7b53e948421b8019fec141d2121', 'baseline operator')
    require(pins['files']['boot/delivery.json'] == 'ea2ff2952a13eddd205ec9ec79e075a42c1a6060c8234f8f6765d03860d7faeb', 'actual IRQ boot delivery')
    require(pins['files']['cohort/delivery.json'] == '3d5b78bc4c7a6b476bfb97c2fbad3e0d76497c94e13bd755a8e4aaa0b032a07b', 'actual cohort')
    return pins['files']


def local_inputs():
    files = source_inputs()
    delivery = read_json(REF / 'charging-ui-audit-20261023/usb-input-irq-boot-candidate/delivery.json')
    require(delivery['passed'] is True and delivery['frozen'] is True, 'boot delivery not frozen')
    require(delivery['candidate_boot']['sha256'] == IRQ_BOOT and delivery['candidate_boot']['bytes'] == SIZES['boot']
            and delivery['rollback_boot_sha256'] == ORIGINAL_BOOT, 'boot delivery identities')
    require(delivery['required_USB_module_sha256'] == '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f', 'paired USB module')
    require(delivery['native_DTB_sha256'] == '13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f', 'native DT identity')
    for which, pair in IMAGES.items():
        require(set(pair) == {'boot'}, 'only boot can be written')
        for _, (image, digest, size) in pair.items():
            require(image.stat().st_size == size and sha(image) == digest, which + ' actual boot image differs')
    identity = read_json(IDENTITY)
    require(identity.get('product') == 'msmnile' and re.fullmatch(r'[A-Za-z0-9._:-]+', identity['serial']), 'private identity')
    return {'images': {k: image_hashes(k) for k in IMAGES},
            'unchanged_logdump_sha256': LOGDUMP502,
            'private_identity_sha256': sha(IDENTITY), 'fastboot_executable_sha256': sha(FASTBOOT),
            'source_files': files, 'activation_pins': pinned_tools()}


def stage_module():
    import importlib.util
    source_inputs()
    spec = importlib.util.spec_from_file_location('irq_actual_stage_proof', STAGE_PROOF)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_context(path, contract=None):
    path = Path(path)
    require(path.name == 'host-context-private.json' and path.is_file() and not path.is_symlink(), 'regular context filename')
    path = path.resolve()
    context = read_json(path)
    require(context['schema'] == 'samurai-usb-irq-protection-fastboot-context-v1', 'context schema')
    txn, token, boot = (context[k] for k in ('transaction_id', 'token', 'old_boot_id'))
    require(re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}', txn)
            and re.fullmatch(r'[0-9a-f]{32,64}', token)
            and re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', boot), 'new activation identity')
    require(path.parent.name == txn, 'new activation directory mismatch')
    keys = {'guard', 'quiesce_state', 'quiesce_summary', 'quiesce_boot_id', 'quiesce_process', 'restart_dispatch', 'restart_claim'}
    require(set(context['files']) == keys, 'context evidence set')
    paths = {k: reference_file(path.parent, v) for k, v in context['files'].items()}
    require(len(set(paths.values())) == len(keys), 'distinct original evidence required')
    guard = read_json(paths['guard'])
    require(context['guard_sha256'] == context['files']['guard']['sha256'], 'guard digest mismatch')
    require(guard['schema'] == 'samurai-usb-irq-protection-activation-v1', 'stage-aware activation schema')
    require((guard['transaction_id'], guard['token'], guard['boot_id']) == (txn, token, boot), 'guard identity differs')
    source_inputs()
    contract = contract or read_json(RESTART / 'prepare-contract.json')
    require(contract['schema'] == 'samurai-usb-irq-protection-activation-contract-v1', 'restart contract schema')
    fixed = contract['fixed_guard_fields']
    require(fixed and all(guard[k] == v for k, v in fixed.items()), 'fixed stage-aware guard fields differ')
    require(guard['kernel_version'] == '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026', 'exact Image502 required')
    for name in ('rootfs_release_sha256', 'soc_serial_sha256', 'compatible_sha256'):
        require(re.fullmatch(r'[0-9a-f]{64}', guard[name]), 'actual board identity missing')
    proof = stage_module()
    reviewed = proof.review_stage(Path(context['stage_directory']), Path(context['stage_fetch_directory']),
                                  expected_transaction=guard['stage']['transaction_id'])
    require(guard['stage'] == proof.guard_stage_fields(reviewed), 'actual source stage proof differs')
    require(reviewed['source_boot_id'] == boot and reviewed['source_version'] == guard['kernel_version'], 'actual stage source boot differs')
    actual_identity = reviewed['identity']
    require(actual_identity == {'boot_id': boot, 'version': guard['kernel_version'],
            'serial_sha256': guard['soc_serial_sha256'], 'compatible_sha256': guard['compatible_sha256'],
            'rootfs_sha256': guard['rootfs_release_sha256']}, 'actual stage board/rootfs identity differs')
    actual_adoption = dict(reviewed['adoption'])
    actual_adoption['fresh_validation_sha256'] = actual_adoption.pop('actual_fresh_validation_sha256')
    require(guard['adoption'] == actual_adoption, 'actual adopted source guard/proof differs')
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
    # An ended SSH child or captured armed phase alone never proves RESTART2.
    # Every action below still requires fresh sole serial/product/geometry.
    return context


def run_action(action, serial, call):
    require(action in ACTIONS, 'unsupported action')
    stdout, _ = call('devices', [FASTBOOT, 'devices'])
    found = re.findall(r'(?m)^(\S+)\s+fastboot\s*$', stdout)
    require(found == [serial] and len(stdout.split()) == 2, 'fresh sole exact fastboot serial required')
    out, err = call('product', [FASTBOOT, '-s', serial, 'getvar', 'product'])
    values = re.findall(r'(?m)^(?:\(bootloader\)\s*)?product:\s*(\S+)\s*$', out + '\n' + err)
    require(values == ['msmnile'], 'fresh product must be exactly msmnile')
    for part in ('boot', 'logdump'):
        out, err = call(part + '-size', [FASTBOOT, '-s', serial, 'getvar', 'partition-size:' + part])
        sizes = re.findall(r'(?m)^(?:\(bootloader\)\s*)?partition-size:' + part + r':\s*(0x[0-9a-fA-F]+|[0-9]+)\s*$', out + '\n' + err)
        require(len(sizes) == 1 and int(sizes[0], 16 if sizes[0].startswith('0x') else 10) == SIZES[part], 'fresh geometry differs: ' + part)
    result = {'fresh_exact_bootloader_identity': True, 'partitions_written': [],
              'runtime_readback_pending': action != 'inspect', 'unchanged_logdump_sha256': LOGDUMP502,
              'rootfs_rollback_proven': False}
    if action in PAIR_ACTIONS:
        which = PAIR_ACTIONS[action]
        pair = IMAGES[which]
        require(set(pair) == {'boot'}, 'write scope is only boot')
        image, digest, size = pair['boot']
        require(image.stat().st_size == size and sha(image) == digest, 'actual boot changed before dispatch')
        out, err = call('flash-boot', [FASTBOOT, '-s', serial, 'flash', 'boot', windows_path(image)])
        text = out + '\n' + err
        require(re.search(r"Writing 'boot'\s+OKAY", text) and 'FAILED' not in text, 'boot write was not confirmed')
        result.update(partitions_written=['boot'], flashed_images_sha256=image_hashes(which), boot_complete=True)
    elif action in REBOOT_IMAGES:
        out, err = call('reboot', [FASTBOOT, '-s', serial, 'reboot'])
        require('FAILED' not in out + err, 'reboot command failed')
        result.update(reboot_command_returned_zero=True, boot_success_proven=False)
    return result


def reboot_binding(directory, action):
    image_action, which = REBOOT_IMAGES[action]
    results = [p for p in directory.glob('*/result-private.json') if p.parent.name in PAIR_ACTIONS]
    require(results, 'reboot requires the corresponding successful boot write')
    latest = max(results, key=lambda p: read_json(p)['claimed_ns'])
    result = read_json(latest)
    require(latest.parent.name == image_action and result['action'] == image_action
            and result['passed'] is True and result['terminal'] is True and result['commands_terminal'] is True
            and result['partitions_written'] == ['boot'] and result['boot_complete'] is True
            and result['flashed_images_sha256'] == image_hashes(which)
            and result['unchanged_logdump_sha256'] == LOGDUMP502, 'last completed image action is not the exact boot')
    return {'image_action': image_action, 'images_sha256': image_hashes(which),
            'image_claim_sha256': sha(latest.parent / 'request-private.json'),
            'image_result_sha256': sha(latest), 'image_claimed_ns': result['claimed_ns']}
