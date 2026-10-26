PROFILES = ('staged_same_boot_old_resident', 'booted_irq_new_resident', 'booted_original_new_resident')
ROLLBACK_PAYLOAD = '5ecae1f5799a1c01d132553b1ad4fb5923d643d1e13fcde8007f5380253fa339'
STAGE_WORKER = '47794e53b8f31e974a968cb6610c69a49e456042be940bca7104bb182595c83a'
STAGE_SUPERVISOR = 'b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc'
VERSION = '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
ROOT = '/root/charging-management-20261023'
SERVICE = '/usr/sbin/samurai-charging'
MANAGER = '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
LIVE_SHA = '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'
STARTUP_SHA = '2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a'
BOOT = '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
IRQ_BOOT = 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
LOGDUMP = 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
LOCK = '/run/lock/samurai-charging.lock'
MANIFEST = '/usr/share/samurai-charging/manifest.json'
USB = '/lib/modules/' + RELEASE + '/extra/samurai-charging/samurai-usb-input.ko'
PROTECTION = '/lib/modules/' + RELEASE + '/extra/samurai-charging/samurai-gauge-protection.ko'
ORDER = [USB, PROTECTION, MANIFEST]


def unpack(request):
    need(set(request) == {'schema', 'transaction_id', 'profile', 'identity', 'source_identity', 'source_stage',
         'activation', 'payload_sha256', 'payload_base64', 'worker_sha256', 'lease_token'}, 'request exact fields')
    need(request['schema'] == 'samurai-usb-irq-protection-rollback-request-v1', 'rollback request schema')
    need(re.fullmatch(r'usb-irq-protection-rollback-[a-z0-9-]{8,48}', request['transaction_id']), 'new rollback transaction')
    need(request['profile'] in PROFILES, 'explicit current identity profile')
    for ident in (request['identity'], request['source_identity']):
        need(set(ident) == {'boot_id', 'version', 'serial_sha256', 'compatible_sha256', 'rootfs_sha256'}, 'actual identity fields')
        need(str(uuid.UUID(ident['boot_id'])) == ident['boot_id'] and ident['version'] == VERSION, 'only actual Image502')
        for key in ('serial_sha256', 'compatible_sha256', 'rootfs_sha256'):
            need(re.fullmatch('[0-9a-f]{64}', ident[key]), 'actual board hash: ' + key)
    need(re.fullmatch('[0-9a-f]{48}', request['lease_token'])
         and re.fullmatch('[0-9a-f]{64}', request['worker_sha256']), 'actual worker/lease')
    raw = base64.b64decode(request['payload_base64'], validate=True)
    need(request['payload_sha256'] == ROLLBACK_PAYLOAD and len(raw) == 44194 and sha(raw) == ROLLBACK_PAYLOAD, 'exact original archive')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        members = tar.getmembers(); need(len(members) == 3, 'exact original three files')
        for member in members:
            target = '/' + member.name
            need(target in OLD_FILES and target not in files and member.name == target.lstrip('/') and member.isfile(), 'original member path/type')
            need(member.mode == 0o600 and member.uid == member.gid == member.mtime == 0
                 and member.uname == member.gname == 'root' and not member.pax_headers, 'original member metadata')
            data = tar.extractfile(member).read(); need(sha(data) == OLD_FILES[target], 'original member bytes')
            files[target] = data
    return files


def active(text):
    if not isinstance(text, str): return None
    values = re.findall(r'\[([^]]+)\]', text)
    return values[0] if len(values) == 1 else text.strip() if not values and len(text.split()) == 1 else None


def expected_profile(request):
    return (BOOT, OLD_NOTES) if request['profile'] == PROFILES[0] else (
        IRQ_BOOT if request['profile'] == PROFILES[1] else BOOT, NEW_NOTES)


def validate_profile(request, actual):
    current, source = request['identity'], request['source_identity']
    need(actual['identity'] == current and current['version'] == VERSION, 'current exact #502/UUID/board identity')
    need(all(current[k] == source[k] for k in ('version', 'serial_sha256', 'compatible_sha256', 'rootfs_sha256')), 'source/current same board/rootfs')
    boot, notes = expected_profile(request)
    need(actual['release'] == RELEASE and actual['machine'] == 'aarch64' and actual['taint'] == '0', 'exact current kernel identity')
    need(actual['boot'] == {'bytes': 100663296, 'sha256': boot}
         and actual['logdump'] == {'bytes': 67108864, 'sha256': LOGDUMP}, 'actual complete carriers')
    need(actual['notes'] == notes and set(actual['module_states']) == set(notes)
         and all(v == 'live' for v in actual['module_states'].values()), 'profile actual resident notes/initstate')
    activation = request['activation']
    if request['profile'] == PROFILES[0]:
        need(current['boot_id'] == source['boot_id'] and activation is None, 'same stage boot/old resident only')
    else:
        need(current['boot_id'] != source['boot_id'], 'must be a new boot, not source UUID')
        # The future host must construct this binding from saved actual action
        # originals using the frozen completion/review_action API. Device does
        # not pretend that digest fields themselves authenticate host commands.
        keys = {'schema', 'activation_transaction_id', 'context_sha256', 'guard_sha256',
                'flash_request_sha256', 'flash_result_sha256', 'reboot_request_sha256', 'reboot_result_sha256',
                'flash_claimed_ns', 'reboot_claimed_ns', 'boot_sha256', 'retained_logdump_sha256', 'action_pair'}
        need(isinstance(activation, dict) and set(activation) == keys, 'explicit saved activation binding')
        need(activation['schema'] == 'samurai-irq-rollback-saved-activation-binding-v1'
             and re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}', activation['activation_transaction_id']), 'independent activation transaction')
        for key in keys - {'schema', 'activation_transaction_id', 'flash_claimed_ns', 'reboot_claimed_ns', 'action_pair'}:
            need(re.fullmatch('[0-9a-f]{64}', activation[key]), 'saved activation hash binding: ' + key)
        need(activation['boot_sha256'] == boot and activation['retained_logdump_sha256'] == LOGDUMP, 'activation profile carrier binding')
        need(type(activation['flash_claimed_ns']) is type(activation['reboot_claimed_ns']) is int
             and 0 < activation['flash_claimed_ns'] < activation['reboot_claimed_ns'], 'original write/reboot order')
        pair = ['flash-candidate', 'reboot-candidate'] if request['profile'] == PROFILES[1] else ['rollback-original', 'reboot-original']
        need(activation['action_pair'] == pair, 'explicit candidate vs original-boot action pair')
    return {'profile': request['profile'], 'resident_notes': notes, 'boot_sha256': boot}


def source_paths(transaction):
    need(re.fullmatch(r'usb-irq-protection-stage-[a-z0-9-]{8,48}', transaction), 'original stage name')
    return {name: ROOT + '/' + transaction + '/' + relative for name, relative in EVIDENCE.items()}


def verify_source_records(request, raws, worker, processes):
    projection = request['source_stage']; tx = projection['transaction_id']; paths = source_paths(tx)
    need(set(projection) == {'transaction_id', 'request_sha256', 'result_sha256', 'host_binding_sha256',
         'worker_sha256', 'supervisor_sha256', 'evidence'} and set(projection['evidence']) == set(paths), 'original source projection')
    need(projection['worker_sha256'] == STAGE_WORKER and projection['supervisor_sha256'] == STAGE_SUPERVISOR, 'original stage source code')
    for name, path in paths.items():
        item = projection['evidence'][name]
        need(set(item) == {'path', 'sha256'} and item['path'] == path and item['sha256'] == sha(raws[name]), 'original stage raw evidence: ' + name)
    need(sha(raws['worker_source']) == STAGE_WORKER and sha(raws['supervisor_source']) == STAGE_SUPERVISOR, 'exact original mutator code')
    need(projection['request_sha256'] == sha(raws['request']) and projection['result_sha256'] == sha(raws['result'])
         and re.fullmatch('[0-9a-f]{64}', projection['host_binding_sha256']), 'original host/request/result binding')
    original = json.loads(raws['request']); worker.unpack(original)
    need(original['transaction_id'] == tx and original['identity'] == request['source_identity'], 'actual original source board/boot')
    chain = verify_chain(raws, original, sha(raws['request']), ROOT + '/' + tx)
    result = verify_stage(raws, original, worker)
    for role in ('worker', 'supervisor'):
        observed = processes[role]
        if request['identity']['boot_id'] != request['source_identity']['boot_id']:
            need(observed == {'state': 'source_boot_ended', 'source_boot_id': request['source_identity']['boot_id'],
                 'current_boot_id': request['identity']['boot_id']}, 'do not attribute current PIDs across boot')
        else:
            need(observed['state'] in ('absent', 'zombie') and observed['pid'] == chain[role + '_pid'], 'original source mutator not ended')
            if observed['state'] == 'zombie': need(observed['start_ticks'] == chain[role + '_start_ticks'], 'same zombie instance')
    return {'source_stage_terminal_verified': True, 'process_chain': chain, 'source_result_sha256': sha(raws['result']),
            'source_boot_id': result['source_boot_id'], 'host_transport_reaudited_here': False}


def safe_electrical(data, now):
    s, r, lim, p = data['sample'], data['state']['registers'], data['limits'], data['protection']
    need(type(data['read_start']) in (int, float) and type(data['read_end']) in (int, float)
         and 0 <= data['read_end'] - data['read_start'] <= 3 and 0 <= now - data['read_end'] <= 1, 'fresh bounded observation')
    need(s.get('valid') == s.get('protection_ok') == 1 and s.get('shadow') == 0
         and type(s.get('age_ms')) is int and 0 <= s['age_ms'] <= 3000, 'fresh complete cell/temperature sample required')
    need(all(type(s.get(key)) is int and 2000000 <= s[key] <= 4600000 for key in ('cell1_uv', 'cell2_uv'))
         and type(s.get('pack_uv')) is int and 4000000 <= s['pack_uv'] <= 9200000
         and abs(s['cell1_uv'] + s['cell2_uv'] - s['pack_uv']) <= 200000, 'safe complete pack/cells')
    need(type(s.get('temp_decic')) is int and 160 <= s['temp_decic'] < 440, 'normal safe temperature')
    need(data['protection_health'] == 'Good' and p.get('id') == 0x2719
         and p.get('error') == p.get('safety') == p.get('pf') == 0, 'fresh independent normal protection')
    need(p.get('operation', 0) & 0x300 == 0x300 and not p['operation'] & ((1 << 20) | (1 << 16) | 0x7c00)
         and p.get('manufacturing', 0) & 0x18 == 0x18 and not p['manufacturing'] & 0x8006, 'sealed autonomous protection')
    need(set(r) == {'00', '01', '02', '03', '04', '05', '07', '08', '09', '0f', '13'}
         and all(type(v) is int and 0 <= v <= 255 for v in r.values()), 'complete nondestructive register set')
    need(type(lim['input_ua']) is type(lim['charge_ua']) is type(lim['cv_pack_uv']) is int
         and 0 <= lim['input_ua'] <= 900000 and 0 <= lim['charge_ua'] <= 250000,
         'actual configured limits within original hard caps')
    need((r['00'] & 0x7f) * 50000 == (r['0f'] & 0x7f) * 50000 == lim['input_ua']
         and (r['02'] & 0x7f) * 50000 == lim['charge_ua'], 'actual register/limit agreement')
    need(7425000 <= lim['cv_pack_uv'] <= 8725000
         and lim['cv_pack_uv'] == 2 * (3712500 + ((r['04'] & 0x7e) >> 1) * 12500), 'bounded inherited CV')
    need(data['state']['driver'] == 'samurai-mp2650' and data['state']['taint'] == '0', 'actual managed untainted charger')
    for name in ('error', 'stop_error', 'latched', 'fault', 'cycle_timeout', 'thermal_inhibit', 'gauge_charge_stop'):
        need(type(s.get(name)) is int, 'known fault history: ' + name)
    need(s['latched'] in (0, 1) and s['cycle_timeout'] in (0, 1), 'known existing latch/timeout')
    # USB source/budget values (including errno/0/unknown) are evidence only.
    # Never infer or raise a budget while restoring inert disk files.


def safe_stopped(data, now):
    safe_electrical(data, now)
    need(active(data['charge_behaviour']) == 'inhibit-charge'
         and data['state']['registers']['08'] & 0x18 == 8, 'physical INHIBIT required')


def idle(data):
    state = data['state']; need(len(state['camera_pm']) == 4 and all(x == 'suspended' for x in state['camera_pm'].values()), 'camera PM idle')
    value = json.loads(state['m2m'])
    need(not any(value.get(k) for k in ('users', 'running', 'fatal', 'pinned', 'orphans', 'first_error')), 'camera m2m idle')


def retained(before, after):
    need(before['notes'] == after['notes'] and before['state']['boot_id'] == after['state']['boot_id'], 'resident/boot unchanged')
    need(before['limits'] == after['limits'], 'configuration limits retained')
    for name, value in before['state']['registers'].items():
        if name == '08': need(after['state']['registers'][name] == (value & ~0x18) | 8, 'only INHIBIT configuration change')
        elif name != '13': need(after['state']['registers'][name] == value, 'other configuration unchanged: ' + name)
    for field in ('latched', 'cycle_timeout'):
        need(not before['sample'][field] or after['sample'][field] == 1, 'prior fault/timeout retained: ' + field)


def restore(request, device, execute=False):
    need(execute, 'explicit --execute-rollback required')
    result = dict(schema='samurai-usb-irq-protection-rollback-result-v1', transaction_id=request.get('transaction_id'),
        profile=request.get('profile'), terminal=True, restored=False, status='not_staged_original', runtime_pending=True,
        phase='request', stop_verified=False, stop_action=None, primary_error=None, disk_state='not_inspected',
        automatic_replay_or_rollback=False, module_or_carrier_action=False, physical_acceptance=False)
    phase = 'request'
    try:
        files = unpack(request)
        phase = 'begin'; device.begin(request)
        phase = 'source-stage'; result['source_proof'] = device.source_proof(request)
        phase = 'identity'; result['current_profile'] = validate_profile(request, device.current(request))
        phase = 'disk'; backups = {target: device.read_owned(target) for target in ORDER}
        for target, (raw, mode) in backups.items(): need(mode == 0o600 and sha(raw) == NEW_FILES[target], 'exact current new disk: ' + target)
        manager = device.manager(); device.verify_retained(manager)
        phase = 'pre-stop'; before = device.observe(manager)
        safe_electrical(before, device.now()); idle(before)
        need(before['notes'] == expected_profile(request)[1], 'actual profile notes before stop')
        device.backup(backups, before)
        phase = 'stop'
        device.check_window(request)
        if active(before['charge_behaviour']) == 'inhibit-charge' and before['state']['registers']['08'] & 0x18 == 8:
            result['stop_action'] = 'already_inhibited'
        else:
            result['stop_action'] = 'manager_stop_once'; device.stop(manager, json.loads(backups[MANIFEST][0]))
        stopped = device.observe(manager); safe_stopped(stopped, device.now()); retained(before, stopped); idle(stopped)
        result['stop_verified'] = True; device.log('stopped-private.json', stopped)
        for target in ORDER:
            phase = 'restore:' + Path(target).name
            device.check_window(request)
            validate_profile(request, device.current(request, carriers=False))
            current = device.observe(manager); safe_stopped(current, device.now()); retained(before, current); idle(current)
            device.replace(target, files[target])
        phase = 'final'
        device.check_window(request); validate_profile(request, device.current(request))
        device.verify_restored(files, manager)
        after = device.observe(manager); safe_stopped(after, device.now()); retained(before, after); idle(after)
        device.log('after-private.json', after)
        result.update(restored=True, phase='staged_original', status='staged_original/runtime_pending',
            disk_state='all_original_fsynced', actual_resident_notes=after['notes'],
            source_budget_observation=after.get('source'), existing_fault_history={key:after['sample'][key]
                for key in ('error','stop_error','latched','fault','cycle_timeout','thermal_inhibit','gauge_charge_stop')},
            old_modules_resident_verified=False, original_full_runtime_accepted=False)
    except BaseException as error:
        result.update(phase='failed',status='failed_preserved_no_replay',primary_error={'phase':phase,'error':detail(error)})
        if isinstance(error, AtomicFailure): result['primary_error']['atomic_stage'] = error.stage
    finally:
        for name, action in [('receipt_error',lambda:device.finish(result)),('close_error',device.close)]:
            try: action()
            except BaseException as error: result.update(restored=False,phase='failed',status='inspect_same_original_worker',**{name:detail(error)})
        try: device.publish(result)
        except BaseException as error: result.update(restored=False,phase='failed',status='inspect_same_original_worker',receipt_error=detail(error))
    return result


class Device:
    def __init__(self):
        self.out = self.lock = self.journal = None; self.events = []; self.request = None; self.carriers = None

    def now(self): return time.clock_gettime(time.CLOCK_BOOTTIME)
    def read_owned(self, path): return read_owned(path)

    def write_new(self, path, raw):
        with Path(path).open('xb') as file: file.write(raw); file.flush(); os.fsync(file.fileno())

    def log(self, name, value):
        self.write_new(self.out / name, encode(value))

    def event(self, value):
        value = dict(value, boottime_s=self.now()); self.events.append(value)
        self.journal.write(encode(value).replace(b'\n', b' ') + b'\n'); self.journal.flush(); os.fsync(self.journal.fileno())

    def check_window(self, request):
        need(self.identity() == request['identity'], 'current source identity unchanged')
        raw, mode = read_owned('/run/' + request['transaction_id'] + '-window-private.json')
        validate_lease(json.loads(raw), mode, request, self.now())

    def identity(self):
        need(os.uname().version == VERSION and os.uname().release == RELEASE and os.uname().machine == 'aarch64', 'only exact current Image502')
        compatible = Path('/sys/firmware/devicetree/base/compatible').read_bytes()
        need(b'realme,samurai' in compatible.split(b'\0'), 'actual board compatible')
        return dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), version=os.uname().version,
            serial_sha256=sha(Path('/sys/devices/soc0/serial_number').read_bytes()), compatible_sha256=sha(compatible),
            rootfs_sha256=sha(read_owned('/etc/samurai-rootfs-release')[0]))

    def begin(self, request):
        import fcntl
        need(os.geteuid() == 0 and not sys.flags.optimize, 'root/nonoptimized')
        self.request = request; root = Path(ROOT) / request['transaction_id']
        info = root.lstat(); need(stat.S_ISDIR(info.st_mode) and not root.is_symlink() and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700, 'unique protected transaction directory')
        need(Path(__file__).resolve() == root / 'restore-worker.py' and sha(read_owned(__file__)[0]) == request['worker_sha256'], 'actual worker path/source')
        self.out = root / 'device-rollback'; self.out.mkdir(mode=0o700, exist_ok=False)
        self.journal = (self.out / 'journal-private.jsonl').open('xb')
        fields = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
        self.log('process-private.json',dict(pid=os.getpid(),start_ticks=int(fields[19]),
            argv=[x.decode() for x in Path('/proc/self/cmdline').read_bytes().split(b'\0') if x],
            boot_id=request['identity']['boot_id'],transaction_id=request['transaction_id'],worker_sha256=request['worker_sha256']))
        self.log('request-private.json',{k:v for k,v in request.items() if k != 'payload_base64'})
        self.check_window(request)
        self.lock = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW)
        info = os.fstat(self.lock); need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o600, 'original service lock')
        fcntl.flock(self.lock,fcntl.LOCK_EX | fcntl.LOCK_NB); self.check_window(request)
        client = Path('/sys/bus/i2c/devices/0-005c')
        need((client/'name').read_text().strip() == 'mp2650' and (client/'driver').resolve().name == 'samurai-mp2650'
             and (client/'of_node').resolve().as_posix().endswith('/soc@0/geniqup@8c0000/i2c@884000/charger@5c'), 'existing exact charger owner')

    def source_proof(self, request):
        paths = source_paths(request['source_stage']['transaction_id']); raws = {}
        for key, path in paths.items(): raws[key] = read_owned(path)[0]
        need(sha(raws['worker_source']) == STAGE_WORKER, 'actual source stage code')
        worker = SimpleNamespace(**runpy.run_path(paths['worker_source']))
        for target in ORDER: raws['backup:' + Path(target).name] = read_owned(Path(paths['result']).parent / (Path(target).name+'.before'))[0]
        original = json.loads(raws['request'])
        proof = read_owned(Path(original['adoption']['guard_path']).parent / 'fresh-validation-private.json')[0]
        saved = json.loads(raws['adoption_proof']); need(sha(proof) == saved['actual_fresh_validation_sha256'], 'actual source adoption raw')
        worker.validate_adoption(json.loads(proof),original)
        different = request['identity']['boot_id'] != request['source_identity']['boot_id']
        processes = {}
        for role in ('worker','supervisor'):
            receipt=json.loads(raws[role+'_process'])
            if different: processes[role] = dict(state='source_boot_ended',source_boot_id=request['source_identity']['boot_id'],current_boot_id=request['identity']['boot_id'])
            else:
                try: fields=Path('/proc',str(receipt['pid']),'stat').read_text().rsplit(')',1)[1].split()
                except FileNotFoundError: processes[role]=dict(state='absent',pid=receipt['pid'])
                else:
                    need(int(fields[19]) == receipt['start_ticks'], 'original PID reused')
                    processes[role]=dict(state='zombie' if fields[0]=='Z' else 'alive',pid=receipt['pid'],start_ticks=int(fields[19]))
        result=verify_source_records(request,raws,worker,processes); self.log('source-stage-proof-private.json',result)
        return result

    def block_fact(self, name, length):
        import fcntl
        fd=os.open('/dev/disk/by-partlabel/'+name,os.O_RDONLY|os.O_CLOEXEC)
        try:
            need(stat.S_ISBLK(os.fstat(fd).st_mode) and struct.unpack('=Q',fcntl.ioctl(fd,0x80081272,bytes(8)))[0]==length,'complete read-only carrier')
            digest=hashlib.sha256(); remaining=length
            while remaining:
                raw=os.read(fd,min(1048576,remaining));need(raw,'short carrier');digest.update(raw);remaining-=len(raw)
            return dict(bytes=length,sha256=digest.hexdigest())
        finally: os.close(fd)

    def current(self, request, carriers=True):
        if carriers: self.carriers={name:self.block_fact(name,length) for name,length in [('boot',100663296),('logdump',67108864)]}
        need(self.carriers is not None,'initial complete carrier read required')
        notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES}
        return dict(identity=self.identity(),release=os.uname().release,machine=os.uname().machine,
            taint=Path('/proc/sys/kernel/tainted').read_text().strip(),notes=notes,
            module_states={name:Path('/sys/module',name.replace('-','_'),'initstate').read_text().strip() for name in notes},**self.carriers)

    def manager(self):
        for path,digest in [(SERVICE,MANAGER),('/usr/lib/samurai-charging/live-session.py',LIVE_SHA),('/usr/local/sbin/samurai-usb',STARTUP_SHA)]: need(sha(read_owned(path)[0])==digest,'retained fixed code: '+path)
        value=runpy.run_path(SERVICE); need(sha(read_owned(SERVICE)[0])==MANAGER and value['live'].REGS==[0,1,2,3,4,5,7,8,9,15,19],'stable manager/no REG14')
        return value

    def verify_retained(self, manager):
        manifest=manager['verify'](); need(manifest==NEW_MANIFEST,'exact current new manifest/retained files')

    def observe(self, manager):
        start=self.now(); live=manager['live']; state=live.state()
        def observed(path):
            try:return Path(path).read_text().strip()
            except OSError as error:return {'errno':error.errno}
        supply=live.PSY/'mp2650-input'; source=live.PSY/'samurai-usb-input'
        protection=Path('/sys/devices/platform/samurai-gauge-protection/protection_state').read_text()
        result=dict(read_start=start,state=state,sample=manager['sample'](),
            notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES},
            protection={k:int(v,0) for k,v in (x.split('=') for x in protection.split())},
            protection_health=(live.PSY/'samurai-gauge-protection/health').read_text().strip(),
            charge_behaviour=(supply/'charge_behaviour').read_text().strip(),
            source={key:observed(source/key) for key in ('online','usb_type','current_max','input_current_limit')},
            limits={key:int((supply/file).read_text()) for key,file in [('input_ua','input_current_limit'),('charge_ua','constant_charge_current'),('cv_pack_uv','constant_charge_voltage')]})
        result['read_end']=self.now();return result

    def stop(self, manager, meta):
        need(sha(read_owned(SERVICE)[0])==MANAGER,'exact normal manager stop')
        result=manager['command'](meta,'stop');need(result=={'managed':True,'requested':'inhibit-charge'},'synchronous stop result')

    def backup(self, files, before):
        for path,(raw,mode) in files.items(): self.write_new(self.out/(Path(path).name+'.before'),raw)
        self.log('before-private.json',before)
        self.log('files-before-private.json',{path:dict(sha256=sha(raw),mode=oct(mode),bytes=len(raw)) for path,(raw,mode) in files.items()})

    def replace(self, path, raw):
        need(path in ORDER and sha(raw)==OLD_FILES[path],'only original fixed file')
        return atomic_replace(path,raw,self.request['transaction_id'],NEW_FILES[path],self.event)

    def verify_restored(self, files, manager):
        for path,raw in files.items(): need(read_owned(path)==(raw,0o600),'old readback')
        need(manager['verify']()==json.loads(files[MANIFEST]),'old manifest/retained files reread; no loaded_matches')

    def finish(self, result):
        if self.out is None:return
        final={}; temporaries={}; labels=[]
        for target in ORDER:
            try:
                raw,mode=read_owned(target);digest=sha(raw)
                label='original' if digest==OLD_FILES[target] else 'new' if digest==NEW_FILES[target] else 'unexpected'
                final[target]=dict(sha256=digest,mode=oct(mode),classification=label)
            except BaseException as error:label='unknown';final[target]=dict(classification=label,error=detail(error))
            labels.append(label)
            temporary=Path(target).with_name('.'+Path(target).name+'.'+self.request['transaction_id']+'.next')
            try:raw,mode=read_owned(temporary);temporaries[target]=dict(path=str(temporary),state='retained',sha256=sha(raw),mode=oct(mode))
            except FileNotFoundError:temporaries[target]=dict(path=str(temporary),state='absent')
            except BaseException as error:temporaries[target]=dict(path=str(temporary),state='unknown',error=detail(error))
        result['final_files']=final;result['temporary_files']=temporaries
        result['unknown_write_state']=any(x in ('unknown','unexpected') for x in labels)
        if all(x=='original' for x in labels): result['disk_state']='all_original_fsynced' if result['restored'] else 'all_original_known_durability_or_acceptance_unproved'
        elif all(x=='new' for x in labels):result['disk_state']='all_new'
        elif set(labels)<={'original','new'}:result['disk_state']='partial_known'
        else:result['disk_state']='unknown_inspect_same_worker'
        if result['restored'] and (result['disk_state']!='all_original_fsynced' or any(x['state']!='absent' for x in temporaries.values())):
            result.update(restored=False,phase='failed',status='final_readback_changed_inspect_same_worker')
        self.log('events-private.json',self.events)

    def close(self):
        errors=[]
        for name in ('journal','lock'):
            value=getattr(self,name)
            if value is not None:
                try:value.close() if name=='journal' else os.close(value)
                except BaseException as error:errors.append(detail(error))
                setattr(self,name,None)
        need(not errors,'cleanup: '+repr(errors))

    def publish(self, result):
        if self.out is not None:self.log('result.json',result)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-rollback',action='store_true');parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args();need(not(args.execute_rollback and args.check_only),'choose inert check or execution')
    if not args.execute_rollback:
        print(json.dumps(dict(source_only=True,device_accessed=False,runtime_request_generated=False,
            profiles=list(PROFILES),payload_sha256=ROLLBACK_PAYLOAD)));return 0
    need(not sys.flags.optimize,'nonoptimized');os.umask(0o077)
    raw=sys.stdin.buffer.read(100001);need(len(raw)<=100000,'bounded request')
    result=restore(json.loads(raw),Device(),execute=True);print(json.dumps(result),flush=True)
    return 0 if result['restored'] else 1


if __name__=='__main__':raise SystemExit(main())
