"""Offline directed migration of the frozen, tested r6 transaction."""
from pathlib import Path
import difflib
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
source = ROOT / 'reference/charging-session-20261023/r6-update/update-r6.py'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'b5cfad278a1d1887e0cb38e47edcb796929b760151e5cb5bb59e775f1e2b2e98'
s = raw.decode().replace('\r\n', '\n')

def change(old, new):
    global s
    assert s.count(old) == 1, old[:100]
    s = s.replace(old, new)

s = s.replace('r5 -> r6', 'r7 -> r8').replace('r6', 'r8').replace('r5', 'r7')
s = s.replace('/var/lib/samurai/k449-adopted/boot-id-private.txt', '/var/lib/samurai/charging-r7-8162b1e7040030d514a83534-adopted/boot-id-private.txt')
s = s.replace('f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf', '5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68')
s = s.replace('944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d', '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f')
s = s.replace('2433d8c04d22bb3e88eb1a2f0ea15c3fc3285706c40695fac6ce605613c57d58', 'f2bcbe500463114a407d93ddb4e2081db179f61dcc35d0a194abb4d18b2a5722')
s = s.replace('fac827cfd3d1d847cb1db82f0a29e451652bd16a996b20666be2d9b330889cb6', '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f')
change("HASHES = {KO:", "SERVICE_SHA = '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'\nHASHES = {KO:")
change("          SERVICE: '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4',\n", '')
change('MODES = {KO: 0o600, SERVICE: 0o755, MANIFEST: 0o600}', 'MODES = {KO: 0o600, MANIFEST: 0o600}')
change('len(raw) == 54604', 'len(raw) == 51100')
change("len(members) == 3, 'exactly three payload files'", "len(members) == 2, 'exactly two payload files; service is read-only'")
change("    expected['installed_files'][SERVICE] = HASHES[SERVICE]\n", "    need(old['installed_files'][SERVICE] == new['installed_files'][SERVICE] == SERVICE_SHA, 'unchanged exact read-only service')\n")
change('only charger/service hashes and r8 revision may change', 'only charger hash and r8 revision may change')
change('def safe_sample(data):\n', '''class UnsafeSample(RuntimeError):
    def __init__(self, message, data):
        super().__init__(message)
        self.sample = dict(data.get('sample', {}))


def safe_sample(data):
    try:
        _safe_sample(data)
    except Exception as error:
        raise UnsafeSample(detail(error), data) from error


def _safe_sample(data):
''')
change("    lim = data['limits']\n    need(50000 <= lim['native_ua'] and 50000 <= lim['input_ua'] <= min(900000, lim['native_ua'])", "    lim = data['limits']\n    source = data['source']\n    need(source['online'] == '1' and int(source['input_current_limit']) == lim['native_ua']\n         and int(source['current_max']) == lim['source_budget_ua'], 'raw native and effective source fields agree')\n    need(50000 <= lim['native_ua'] and 50000 <= lim['source_budget_ua'] <= 2000000\n         and 50000 <= lim['input_ua'] <= min(900000, lim['source_budget_ua'])")
change("s.get('budget_ua') == lim['native_ua'], 'fresh sample/source budget agreement'", "s.get('budget_ua') == lim['source_budget_ua'], 'fresh sample/effective source budget agreement'")
change("    return 'full_holding' if full else 'managed'", "    need(160 <= s.get('temp_decic', -999) < 440, 'this update window requires the NORMAL band')\n    if 'thermal_band' in s:\n        need(s['thermal_band'] == 4, 'new OEM thermal band must remain NORMAL')\n    return 'full_holding' if full else 'managed'")
change("    need(before['state']['taint'] == after['state']['taint'] == '0', 'taint must remain zero')", "    need(before['state']['taint'] == after['state']['taint'] == '0', 'taint must remain zero')\n    services = before['state']['services']\n    need(len(services) == 4 and {s['comm'] for s in services} == {'phoc', 'phosh', 'pipewire', 'wireplumber'}\n         and all(s['uid'] == 10000 and s['pid'] > 0 for s in services), 'four actual UID10000 session services')\n    need(all(value == 'suspended' for value in before['state']['camera_pm'].values())\n         and len(before['state']['camera_pm']) == 4, 'camera runtime PM must be idle')\n    m2m = json.loads(before['state']['m2m'])\n    need(all(m2m.get(key) == 0 for key in ['users', 'orphans', 'jobs', 'first_error'])\n         and all(m2m.get(key) is False for key in ['running', 'fatal', 'pinned']), 'camera m2m must be idle')")
change("\n        manager = io.manager(sha(backup[SERVICE][0]))", "\n        service_raw, service_mode = io.read_owned(SERVICE)\n        need(sha(service_raw) == SERVICE_SHA and service_mode == 0o755, 'exact read-only service identity/mode')\n        manager = io.manager(SERVICE_SHA)")
change("need(before['limits']['native_ua'] == before['limits']['input_ua'] == 100000, 'current SDP baseline 100mA')", "need(before['limits']['native_ua'] == before['limits']['source_budget_ua'] == before['limits']['input_ua'] == 100000\n             and '[SDP]' in before['source']['usb_type'], 'current real SDP native/effective/physical baseline 100mA')")
change("        io.backup(backup, before)", "        io.backup(backup, before)\n        result['before_session_seconds'] = before['sample']['session_seconds']\n        result['volatile_cycle_reload_boundary'] = True\n        result['service_read_only_sha256'] = SERVICE_SHA")
change("        phase = 'install-three-files'\n        for name in [KO, SERVICE, MANIFEST]:", "        phase = 'install-two-files'\n        for name in [KO, MANIFEST]:")
s = s.replace('io.manager(HASHES[SERVICE])', 'io.manager(SERVICE_SHA)')
change("        phase = 'new-start'", "        phase = 'new-inhibited-sample'\n        result['new_inhibited_sample'] = io.inhibited_ready(manager, request)['sample']\n        phase = 'new-start'")
change("        result['primary_error'] = {'phase': phase, 'error': detail(error)}", "        result['primary_error'] = {'phase': phase, 'error': detail(error)}\n        if isinstance(error, UnsafeSample):\n            result['first_unsafe_sample'] = error.sample")
change("        need(after['limits']['native_ua'] == before['limits']['native_ua'], 'native budget changed during acceptance')\n        need(after['limits']['cv_uv'] <= before['limits']['cv_uv'], 'inherited CV ceiling increased')", "        need(after['limits'] == before['limits'], 'NORMAL SDP100 input/charge/CV/effective budget must match r7 exactly')\n        need(after['source'] == before['source'], 'source changed during acceptance')")
change("        result['accepted_state'] = healthy(after, allow_full=True)", "        result['accepted_state'] = healthy(after, allow_full=True)\n        need(after['sample'].get('thermal_band') == 4 and 'band_pre_shake' in after['sample'], 'complete r8 NORMAL thermal telemetry')")
start = s.index('                resume_allowed = True\n')
end = s.index('            except Exception as recovery_error:', start)
s = s[:start] + '''                retained = False
                if io.module_present():
                    need(io.module_state() == 'live', 'recover only a known live module')
                    manager = io.manager_for_stop()
                    current = None
                    try:
                        current = io.observe(manager)
                        safe_sample(current)
                        need(not isinstance(error, UnsafeSample), 'earlier observed unsafe sample remains disqualifying')
                    except Exception as sample_error:
                        if io.uncertain:
                            raise
                        # Preserve the live module's fault/timeout/history. A
                        # reload followed by AUTO would erase a transient latch.
                        result['recovery_withheld_reason'] = detail(sample_error)
                        result['recovery_withheld_sample'] = current.get('sample') if current else None
                        stopped(io, manager, old)
                        try:
                            current_meta = io.verify(manager)
                            need(sha(io.read_owned(MANIFEST)[0]) in (OLD, NEW), 'known coherent installed version')
                            io.notes_match(manager, current_meta)
                            result['recovery_state'] = current_meta['adapter_revision'] + '-consistent-inhibited; unsafe sample retained; no unload/AUTO'
                        except Exception as coherence_error:
                            if io.uncertain:
                                raise
                            result['recovery_coherence_error'] = detail(coherence_error)
                            # Only an already inconsistent installation may need
                            # disk repair. Never unload its unsafe live module.
                            repaired = []
                            if changed:
                                for name in [KO, MANIFEST]:
                                    io.replace(name, backup[name][0], backup[name][1])
                                    repaired.append(name)
                            result['repaired_disk_files'] = repaired
                            result['runtime_disk_mismatch_requires_review'] = True
                            result['recovery_state'] = 'unsafe-live-module-inhibited; r7 disk repair only; no unload/AUTO'
                        result['observed_unsafe_state_preserved_in_live_module'] = True
                        retained = True
                    if not retained:
                        stopped(io, manager, old)
                        io.unload()
                if not retained:
                    if changed:
                        for name in [KO, MANIFEST]:
                            io.replace(name, backup[name][0], backup[name][1])
                    manager = io.manager(SERVICE_SHA)
                    need(io.verify(manager) == old, 'fresh restored r7 service verify')
                    io.load(KO)
                    io.notes_match(manager, old)
                    result['restored_inhibited_sample'] = io.inhibited_ready(manager, request)['sample']
                    io.check_window(request)
                    io.manager_command(manager, old, 'start')
                    recovered = io.observe(manager)
                    healthy(recovered, allow_full=True)
                    unchanged(before, recovered)
                    need(recovered['limits']['cv_uv'] <= before['limits']['cv_uv'], 'restored CV ceiling')
                    result['recovery_state'] = 'r7-managed-current-source-budget'
''' + s[end:]
change("        need(digest in (HASHES[SERVICE], '4165b06ca7e6169c778d72e6dd604b89274ad29c87e15a7c03cc5a38dc21ea00'), 'only known manager code may stop')", "        need(digest == SERVICE_SHA, 'only exact unchanged manager code may stop')")
change("        return {'state': state, 'sample': manager['sample'](), 'registers': state['registers'], 'notes': notes,", "        source = {key: (live.PSY / 'samurai-usb-input' / key).read_text().strip()\n                  for key in ['online', 'usb_type', 'current_max', 'input_current_limit']}\n        return {'state': state, 'sample': manager['sample'](), 'registers': state['registers'], 'notes': notes, 'source': source,")
change("'native_ua': int((live.PSY / 'samurai-usb-input/input_current_limit').read_text()),", "'native_ua': int(source['input_current_limit']),\n                           'source_budget_ua': int(source['current_max']),")
change("    def manager_command(self, manager, meta, action):", '''    def inhibited_ready(self, manager, request):
        # A newly probed module starts with valid=0/error=-ENODATA. Only that
        # documented initialization state may wait, at most three seconds.
        deadline = time.monotonic() + 3
        while True:
            self.check_window(request)
            current = self.observe(manager)
            s = current['sample']
            initializing = (s.get('valid') == 0 and s.get('error') == -61
                            and all(s.get(key, -1) == 0 for key in
                                    ['latched', 'fault', 'stop_error', 'cycle_timeout', 'source_inhibit', 'thermal_inhibit']))
            need(current['registers']['08'] & 0x18 == 8, 'pre-AUTO synchronous INHIBIT readback')
            if not initializing:
                safe_sample(current)
                need(160 <= s.get('temp_decic', -999) < 440, 'pre-AUTO NORMAL band')
                return current
            need(time.monotonic() < deadline, 'new module never produced a fresh safe inhibited sample')
            time.sleep(.2)

    def manager_command(self, manager, meta, action):''')
change("        actual = sha(self.read_owned(SERVICE)[0])", "        need(not self.uncertain, 'unknown child/module: no further manager mutation')\n        actual = sha(self.read_owned(SERVICE)[0])")
s = s.replace('only exact triad and original modes', 'only exact charger/manifest pair and original modes')
s = s.replace('three-files', 'two-files')
change("def stopped(io, manager, meta):\n    # A raised stop is a failed transaction even if a later readback is paused.\n    need(io.module_state() == 'live', 'stop only a known live module')\n    io.manager_command(manager, meta, 'stop')\n    need(io.registers()['08'] & 0x18 == 8, 'synchronous INHIBIT hardware readback')", "def stopped(io, manager, meta, result=None):\n    # A raised stop is a failed transaction even if a later readback is paused.\n    try:\n        need(io.module_state() == 'live', 'stop only a known live module')\n        io.manager_command(manager, meta, 'stop')\n        need(io.registers()['08'] & 0x18 == 8, 'synchronous INHIBIT hardware readback')\n    except Exception as error:\n        if result is not None:\n            result['stop_error'] = detail(error)\n        raise")
s = s.replace('stopped(io, manager, old)', 'stopped(io, manager, old, result)').replace('stopped(io, io.manager_for_stop(), old)', 'stopped(io, io.manager_for_stop(), old, result)')
change("                result['recovery_error'] = detail(recovery_error)", "                result['recovery_error'] = detail(recovery_error)\n                result['recovery_state'] = 'recovery-failed; live-module safety stop only; operator review'")
change("    answer = update(json.loads(sys.stdin.buffer.read()), device)\n    print(json.dumps(answer), flush=True)", "    try:\n        answer = update(json.loads(sys.stdin.buffer.read()), device)\n        print(json.dumps(answer), flush=True)\n    except BaseException:\n        if not device.uncertain:\n            raise\n        # A failed receipt/stdout must not release the lock while a mutating\n        # child is unknown. Launcher must fetch this same quarantined worker.\n        while True:\n            time.sleep(1)")
assert 'HASHES[SERVICE]' not in s and 'backup[SERVICE]' not in s
assert 'for name in [KO, SERVICE, MANIFEST]' not in s
(HERE / 'update-r8.py').write_text(s, encoding='utf-8', newline='\n')
(HERE / 'migration.patch').write_text(''.join(difflib.unified_diff(raw.decode().splitlines(True), s.splitlines(True), fromfile='r6-update/update-r6.py', tofile='r8-update/update-r8.py')), encoding='utf-8', newline='\n')
print(hashlib.sha256(s.encode()).hexdigest())
