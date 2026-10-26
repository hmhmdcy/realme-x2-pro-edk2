"""Current adopted-boot PM evidence. Default checks local files only."""
from pathlib import Path
import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import types
import uuid

sys.dont_write_bytecode = True
if sys.flags.optimize:
    raise RuntimeError('non-optimized Python required')
HERE = Path(__file__).resolve().parent
PRIMITIVE_SHA256 = 'fd3fd4bef1e04dc8a29b5240cad8989d700021e353e081c0fcf0b297e4bda0a1'
POST_SHA256 = '8da495324ea341714f193d8406ec860a93733971599f2c50e8c51c7a88ba4ab2'
LIVE_SHA256 = '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'
CAMERA = ['ac10000.icp', 'acb3000.camss', 'ac4a000.cci', 'ac4b000.cci']
SERVICES = ['phoc', 'phosh', 'pipewire', 'wireplumber']
FAULTS = ['WARNING:', 'Oops:', 'refcount_t: underflow', 'gpu fault:', 'NGD resume failed']
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def load_bytes(raw, name, filename):
    module = types.ModuleType(name)
    module.__file__ = filename
    exec(compile(raw, filename, 'exec'), module.__dict__)
    return module


def trace_module():
    return load_bytes((HERE / 'trace-evidence.py').read_bytes(), 'pm_trace_evidence', str(HERE / 'trace-evidence.py'))


def validate_request(c):
    if c.get('schema') != 'samurai-pm-current-evidence-v1':
        raise ValueError('current PM request required')
    if not re.fullmatch(r'charging-pm-current-[a-z0-9][a-z0-9-]{0,32}', c.get('transaction', '')):
        raise ValueError('unique current PM transaction required; old transactions cannot be reused')
    d = c['adopted']
    if str(uuid.UUID(d['boot'])) != d['boot'] or not d['version'].startswith('#502 '):
        raise ValueError('actual adopted #502 boot required')
    if d['guard'] != '/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt':
        raise ValueError('wrong adopted guard')
    if not (c['pointer']['guard_path'] == d['guard'] and c['pointer']['Image502_verified'] is True
            and c['pointer']['original_key_verified'] is True and c['pointer']['baseline481_verified'] is True
            and c['pointer']['candidate_boot_sha256'] == d['candidate_boot_sha256'] == '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
            and c['pointer']['candidate_logdump_sha256'] == d['candidate_logdump_sha256'] == 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
            and c['pointer']['charging_manifest_sha256'] == d['manifest'] == '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'):
        raise ValueError('adopted pointer/profile differs')
    if c.get('alarm_delay_seconds') != 15 or c.get('required_console_and_RTC_observation') is not True:
        raise ValueError('fixed observed PM scope required')
    if not Path(c['output_root']).is_absolute():
        raise ValueError('absolute output root required')
    for name, digest in c['bundle_sha256'].items():
        if name not in ['worker.py', 'trace-evidence.py', 'pm-transaction.py'] or sha((HERE / name).read_bytes()) != digest:
            raise ValueError('tested PM bundle changed')
    if set(c['bundle_sha256']) != {'worker.py', 'trace-evidence.py', 'pm-transaction.py'}:
        raise ValueError('PM bundle incomplete')
    if c['bundle_sha256']['pm-transaction.py'] != PRIMITIVE_SHA256:
        raise ValueError('primitive changed')
    for name, expected in [('postboot', POST_SHA256), ('live_state', LIVE_SHA256)]:
        source = c['sources'][name]
        body = base64.b64decode(source['base64'], validate=True)
        if source['sha256'] != expected or sha(body) != expected:
            raise ValueError('reviewed read-only input changed')

def healthy(s):
    # This classifies a fresh sample only; every other PM acceptance gate stays
    # independent. A normal Full is charge-only hold, never operator INHIBIT.
    common = (all(s.get(k) == 1 for k in ['valid', 'online', 'protection_ok'])
              and s.get('shadow') == 0 and 0 <= s.get('age_ms', -1) < 2000
              and s.get('budget_ua', 0) >= 50000
              and all(s.get(k) == 0 for k in ['error', 'stop_error', 'latched', 'source_inhibit', 'fault']))
    if not common:
        return False
    if s.get('desired_enable') == 1:
        return True  # Existing managed sample contract.
    return (s.get('desired_enable') == 0
            and all(s.get(k) == 1 for k in ['logical_full', 'hold_requested', 'full_holding'])
            and type(s.get('full_cause')) is int and s['full_cause'] in [1, 2, 3]
            and s.get('session_seconds') == 0
            and s.get('gauge_charge_stop') == 0 and s.get('cycle_timeout') == 0
            and type(s.get('flags')) is int and 0 <= s['flags'] <= 0xffff
            and not s['flags'] & 0xc000)

def services(state):
    return {name: sorted((p['pid'], p['uid']) for p in state['services'] if p['comm'] == name)
            for name in SERVICES}

def configuration_preserved(before, after):
    old = {k: v for k, v in before['state']['registers'].items() if k != '13'}
    new = {k: v for k, v in after['state']['registers'].items() if k != '13'}
    if old == new:
        return True
    # A newly established safe Full may clear only CHG_EN. Input converter,
    # all limits and every other register bit must match the managed baseline.
    first, last = before['sample'], after['sample']
    if not (healthy(first) and first.get('desired_enable') == 1
            and healthy(last) and last.get('desired_enable') == 0):
        return False
    a, b = old.get('08'), new.get('08')
    if not (type(a) is int and type(b) is int and a & 0x18 == 0x10 and b & 0x18 == 0):
        return False
    old['08'] = a & ~0x10
    return old == new

def audit_trace(text):
    starts = re.compile(r'\s(\d+\.\d+): device_pm_callback_start: (\S+) (\S+), parent: [^,]+, ([^\[]*)\[([^\]]+)\]')
    ends = re.compile(r'\s(\d+\.\d+): device_pm_callback_end: (\S+) (\S+), err=(-?\d+)')
    targets = ['0-005c', 'samurai-usb-input', 'samurai-gauge-protection', '5-0055']
    pending, records, errors = {}, [], []
    header = re.search(r'entries-in-buffer/entries-written:\s*(\d+)/(\d+)', text)
    if not header or header[1] != header[2] or int(header[1]) == 0:
        errors.append('trace completeness/overflow header unproven')
    for line in text.splitlines():
        m = starts.search(line)
        if m and m[3] in targets:
            key = (m[2], m[3])
            if key in pending:
                errors.append('overlapping callback: ' + m[3])
            pending[key] = {'driver': m[2], 'device': m[3], 'ops': m[4].strip(),
                            'phase': m[5], 'start': float(m[1])}
        m = ends.search(line)
        if m and m[3] in targets:
            key = (m[2], m[3])
            row = pending.pop(key, None)
            if row is None:
                errors.append('unmatched callback end: ' + m[3])
            else:
                records.append({**row, 'end': float(m[1]), 'error': int(m[4])})
    if pending:
        errors.append('unfinished callbacks')
    selected = {}
    for device in targets:
        for phase in ['suspend', 'resume']:
            rows = [r for r in records if r['device'] == device and r['phase'] == phase and r['ops']]
            if len(rows) != 1 or rows[0]['error'] != 0 or rows[0]['end'] < rows[0]['start']:
                errors.append('missing/failed callback: ' + device + '/' + phase)
            else:
                selected[device, phase] = rows[0]
    if not errors:
        for device in targets[1:]:
            if not (selected['0-005c', 'suspend']['end'] <= selected[device, 'suspend']['start']
                    and selected[device, 'resume']['end'] <= selected['0-005c', 'resume']['start']):
                errors.append('supplier order: ' + device)
    return {'passed': not errors, 'errors': errors, 'callbacks': records}


def preflight(c, before):
    d = c['adopted']
    reasons = []
    if not (before.get('boot_id') == d['boot'] and before.get('release') == d['release']
            and before.get('manifest_sha256') == d['manifest'] and before.get('adopted_identity_verified')):
        reasons.append('current adopted identity differs')
    state = before['state']
    if state.get('taint') != '0' or state.get('driver') != 'samurai-mp2650':
        reasons.append('charger driver or taint')
    if not all(state.get('camera_pm', {}).get(name) == 'suspended' for name in CAMERA):
        reasons.append('camera not suspended')
    m2m = json.loads(state.get('m2m', '{}'))
    if not all(m2m.get(k) == v for k, v in {'users': 0, 'running': False, 'fatal': False,
                                          'pinned': False, 'orphans': 0, 'first_error': 0}.items()):
        reasons.append('camera resource state not idle')
    if not all(len(rows) == 1 and rows[0][1] == 10000 for rows in services(state).values()):
        reasons.append('four user services not established')
    if not healthy(before.get('sample', {})) or not before.get('charging_profile_healthy'):
        reasons.append('fresh protection/source/Full charging profile unproved')
    if not before.get('modules_exact') or not before.get('read_only_prerequisites') or not before.get('postboot_profile_passed'):
        reasons.append('current R8/camera/services/PM prerequisites incomplete')
    if not before['trace_capability']['passed']:
        reasons += before['trace_capability']['errors']
    return reasons


def classify(c, before, primitive, after, text, cleanup, trace_details):
    """Preserve functional facts even when unique cause or host recovery is unknown."""
    helper = trace_module()
    wakeup = after['wakeup_irq'] if after else {'available': False, 'value': None, 'errno': None}
    evidence = helper.analyze(text, primitive, before['trace_capability'], wakeup)
    callbacks = audit_trace(text)
    checks = {'primitive_returned': primitive.get('mem_returned') is True and primitive.get('outcome') == 'returned',
              'planned_residency_observed': 10 <= primitive.get('estimated_residency_seconds', -1) <= 20,
              'own_alarm_cleanup_safe': primitive.get('cleanup') in ['alarm_already_consumed_or_cleared', 'owned_alarm_cancelled'] and not primitive.get('cleanup_error'),
              'trace_complete_callbacks_ordered': callbacks['passed'],
              'trace_cleanup_safe': cleanup.get('passed') is True,
              'post_evidence_collected': after is not None}
    functional = {'returned': primitive.get('mem_returned') is True,
                  'estimated_residency_seconds': primitive.get('estimated_residency_seconds'),
                  'planned_residency_observed': checks['planned_residency_observed'],
                  'post_conditions': None,
                  'host_NCM_and_strict_key_recovery': 'not_collected_by_this_worker'}
    if after is not None:
        log = helper.log_suffix(before['dmesg'], after['dmesg'])
        checks.update(same_adopted_boot=after.get('adopted_identity_verified') is True and after['boot_id'] == before['boot_id'] == c['adopted']['boot'],
                      manifest_and_modules=after['manifest_sha256'] == before['manifest_sha256'] and after['modules_exact'],
                      safe_charging=healthy(after['sample']) and after['charging_profile_healthy'],
                      configuration_preserved=configuration_preserved(before, after),
                      native_allowance_preserved=after['allowance'] == before['allowance'] and after['allowance'] >= 50000,
                      source_budget_preserved=after['source']['current_max'] == before['source']['current_max'],
                      same_four_services=services(after['state']) == services(before['state']),
                      same_camera=after['state']['camera_pm'] == before['state']['camera_pm'] and after['state']['m2m'] == before['state']['m2m'],
                      taint_zero=after['state']['taint'] == '0',
                      no_recorded_new_faults=log['complete_since_baseline'] and not any(token in '\n'.join(log['new_lines']) for token in FAULTS))
        a, b = before['stats'], after['stats']
        checks['suspend_stats_success'] = (type(a.get('success')) is int and type(b.get('success')) is int and b['success'] == a['success'] + 1
                                            and type(a.get('fail')) is int and b.get('fail') == a['fail']
                                            and all(b.get(k) == v for k, v in a.items() if k.startswith('failed_')))
        functional['post_conditions'] = {'source': after['source'], 'hardware_input': after['hardware_input'],
                                          'native_allowance_ua': after['allowance'], 'charging_profile_healthy': after['charging_profile_healthy'],
                                          'services_preserved': checks['same_four_services'], 'phone_USB_software': after['udc'],
                                          'RTC_irq_delta': after['rtc_irq'] - before['rtc_irq'] if type(after['rtc_irq']) is int and type(before['rtc_irq']) is int else None,
                                          'log_continuity': {k: v for k, v in log.items() if k != 'new_lines'}}
    return {'local_functional_checks_passed': all(checks.values()), 'functional_checks': checks,
            'functional_facts': functional, 'trace_evidence': evidence, 'callback_audit': callbacks,
            'trace_details': trace_details,
            'passed': False, 'whole_system_accepted': False,
            'whole_system_reason': 'root must separately integrate actual host NCM and strict-key data restoration; unique cause is independently reported'}


def dispatch(c, board):
    validate_request(c)
    board.create_new(c)
    result = {'terminal': True, 'passed': False, 'whole_system_accepted': False, 'classification': 'preflight_rejected'}
    before = primitive = after = None
    text, details, cleanup, stage = '', {}, {'passed': True, 'owned': False}, 'preflight'
    try:
        before = board.capture(c, before=True)
        board.save('before-private.json', before)
        reasons = preflight(c, before)
        board.save('preflight-result.json', {'passed': not reasons, 'reasons': reasons})
        if reasons:
            result['preflight_reasons'] = reasons
        else:
            stage = 'trace_setup'
            board.start_trace(before['trace_capability'])
            stage = 'primitive'
            primitive = board.suspend_once()
            board.save('primitive-result.json', primitive)
            stage = 'trace_stop'
            text, details = board.finish_trace()
            stage = 'post_evidence'
            if primitive.get('outcome') == 'returned':
                board.wait_for_fresh_sample()
            after = board.capture(c, before=False)
            board.save('after-private.json', after)
            result['classification'] = 'evidence_collected'
    except BaseException as error:
        result.update(failed_stage=stage, classification='preflight_rejected' if stage == 'preflight' else 'evidence_or_operation_failed',
                      error={'type': type(error).__name__, 'message': str(error)})
    finally:
        try:
            extra = board.cleanup_trace_if_owned()
        except BaseException as error:
            extra = {'passed': False, 'owned': True, 'errors': [{'type': type(error).__name__, 'message': str(error)}]}
        if extra is not None:
            cleanup = extra
            board.save('trace-cleanup-result.json', extra)
        # A post-evidence/cleanup error must not erase the real mem return/duration.
        if before is not None and primitive is not None:
            result.update(classify(c, before, primitive, after, text, cleanup, details))
        board.save('result.json', result)
    return result


class RealBoard:
    def __init__(self, c):
        self.c, self.out, self.trace = c, None, None
        self.helper = trace_module()
        self.pm = load_bytes((HERE / 'pm-transaction.py').read_bytes(), 'reviewed_pm', str(HERE / 'pm-transaction.py'))
        board = self
        class ObservedPMIO(self.pm.SysfsPMIO):
            def write_alarm(self, target):
                if target:
                    board.trace.ready_to_arm()
                super().write_alarm(target)
        self.io = ObservedPMIO(self.phase)
        self.post = load_bytes(base64.b64decode(c['sources']['postboot']['base64'], validate=True), 'reviewed_postboot', '<pinned-postboot>')
        self.live = load_bytes(base64.b64decode(c['sources']['live_state']['base64'], validate=True), 'reviewed_live', '<pinned-live-state>')

    def create_new(self, c):
        self.out = Path(c['output_root']) / c['transaction']
        self.out.mkdir(mode=0o700)  # existing transaction, including unknown, refuses replay
        self.save('request-private.json', c)
        self.save('worker-intent-private.json', {'pid': os.getpid(), 'argv': sys.argv,
                  'startticks': int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]), 'request_count': 1})

    def save(self, name, value):
        target = self.out / name
        temporary = target.with_suffix('.next')
        with temporary.open('w') as stream:
            json.dump(value, stream, indent=2); stream.flush(); os.fsync(stream.fileno())
        temporary.replace(target)

    def phase(self, entry):
        value = {'pid': os.getpid(), **entry}
        with (self.out / 'phases-private.jsonl').open('a') as stream:
            stream.write(json.dumps(value) + '\n'); stream.flush(); os.fsync(stream.fileno())
        self.save('phase-private.json', value)

    def identity(self):
        d = self.c['adopted']
        if not (Path('/proc/sys/kernel/random/boot_id').read_text().strip() == d['boot'] == Path(d['guard']).read_text().strip()
                and os.uname().release == d['release'] and os.uname().version == d['version']
                and sha(Path('/etc/samurai-rootfs-release').read_bytes()) == d['rootfs']
                and sha(Path('/sys/devices/soc0/serial_number').read_bytes()) == d['serial_sha256']
                and sha(Path('/sys/firmware/devicetree/base/compatible').read_bytes()) == d['compatible_sha256']):
            raise ValueError('current adopted boot/guard/board/rootfs differs before hardware inspection')
        for name, digest in d['notes'].items():
            parent = Path('/sys/module') / name
            if parent.joinpath('initstate').read_text().strip() != 'live' or sha(parent.joinpath('notes/.note.gnu.build-id').read_bytes()) != digest:
                raise ValueError('current loaded identity differs: ' + name)

    def console_inventory(self):
        consoles = Path('/proc/consoles').read_text()
        names = {line.split()[0] for line in consoles.splitlines() if line.split()}
        expected = {('pr/' + name)[:15] for name in names}
        producers = []
        for p in Path('/proc').iterdir():
            if not p.name.isdigit():
                continue
            try:
                comm = (p / 'comm').read_text().strip()
                if comm in expected:
                    ticks = int((p / 'stat').read_text().rsplit(')', 1)[1].split()[19])
                    producers.append({'pid': int(p.name), 'comm': comm, 'startticks': ticks})
            except (OSError, ValueError, IndexError):
                continue
        return {'consoles': consoles, 'active': Path('/sys/class/tty/console/active').read_text(), 'producers': producers,
                'printk': Path('/proc/sys/kernel/printk').read_text(),
                'console_suspend': Path('/sys/module/printk/parameters/console_suspend').read_text(),
                'ignore_loglevel': Path('/sys/module/printk/parameters/ignore_loglevel').read_text()}

    def capture(self, c, before):
        self.identity()
        raw = self.post.collect(c['adopted']['postboot_request'])
        audit = self.post.audit(raw, c['adopted']['postboot_request'])
        # Identity again before the established read-only I2C register helper.
        self.identity()
        state = self.live.state()
        sample = self.post.parse_kv(Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text())
        stats = {p.name: int(p.read_text().strip()) for p in Path('/sys/power/suspend_stats').iterdir()
                 if p.is_file() and re.fullmatch(r'\d+', p.read_text().strip())}
        console = self.console_inventory()
        if before:
            self.before_console = console
        capability = self.helper.inspect(self.helper.TraceIO(), os.getpid(), [r['pid'] for r in console['producers']])
        prerequisites = (os.geteuid() == 0 and Path('/sys/power/mem_sleep').read_text().strip() == '[s2idle]'
                         and Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip() == 'enabled')
        if before:
            prerequisites = (prerequisites and not json.loads(Path('/var/lib/samurai/gnss-assist/watch-state.json').read_text())['active']
                             and all(p.read_text().strip() == 'closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
                             and all('powered=0 muted=1' in Path('/sys/bus/i2c/devices', addr, 'status').read_text() for addr in ['1-0039', '1-003a']))
        checks = audit.get('checks', {})
        return {'boot_id': state['boot_id'], 'release': state['release'], 'manifest_sha256': raw['manifest']['sha256'],
                'adopted_identity_verified': True, 'state': state, 'sample': sample, 'stats': stats,
                'rtc_irq': capability.get('rtc', {}).get('count'), 'rtc_irq_number': capability.get('rtc', {}).get('irq'),
                'wakeup_irq': capability['wakeup_irq'], 'trace_capability': capability, 'console_inventory': console,
                'modules_exact': checks.get('R8_install', {}).get('R8_disk_and_live_notes') is True,
                'postboot_profile_passed': audit['passed'], 'postboot_audit': audit, 'postboot_raw': raw,
                'charging_profile_healthy': checks.get('charging', {}).get('ready') is True,
                'read_only_prerequisites': prerequisites, 'source': raw['source'], 'hardware_input': raw['charger'],
                'udc': raw['udc'], 'allowance': int(raw['source']['input_current_limit']),
                'dmesg': raw['dmesg']['stdout']}

    def start_trace(self, capability):
        # No arbitrary PID list: revalidate the exact producers from preflight.
        for producer in self.before_console['producers']:
            p = Path('/proc') / str(producer['pid'])
            if (p / 'comm').read_text().strip() != producer['comm'] or int((p / 'stat').read_text().rsplit(')', 1)[1].split()[19]) != producer['startticks']:
                raise ValueError('actual console producer changed before trace setup')
        self.trace = self.helper.Session(self.helper.TraceIO(), capability, self.c['transaction'], self.save_trace)
        self.trace.setup()

    def save_trace(self, text):
        with (self.out / 'pm-trace-private.txt').open('w') as stream:
            stream.write(text); stream.flush(); os.fsync(stream.fileno())

    def finish_trace(self):
        return self.trace.stop()

    def cleanup_trace_if_owned(self):
        return self.trace.cleanup() if self.trace is not None else None

    def suspend_once(self):
        self.identity()
        return self.pm.suspend_once(self.io)

    def wait_for_fresh_sample(self):
        time.sleep(3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request'); parser.add_argument('--request-sha256')
    parser.add_argument('--inspect-current', action='store_true')
    parser.add_argument('--execute', action='store_true'); parser.add_argument('--window-confirmed', action='store_true')
    a = parser.parse_args()
    if not a.inspect_current and not a.execute:
        for name in ['worker.py', 'trace-evidence.py', 'pm-transaction.py']:
            ast.parse((HERE / name).read_bytes())
        if sha((HERE / 'pm-transaction.py').read_bytes()) != PRIMITIVE_SHA256:
            raise ValueError('primitive changed')
        print(json.dumps({'local_source_checked': True, 'device_accessed': False, 'whole_system_accepted': False}))
        return 0
    if not a.window_confirmed or not a.request or not re.fullmatch(r'[0-9a-f]{64}', a.request_sha256 or ''):
        raise ValueError('actual request/hash and current owned window required')
    raw = Path(a.request).read_bytes()
    if sha(raw) != a.request_sha256:
        raise ValueError('actual request changed')
    c = json.loads(raw); validate_request(c)
    board = RealBoard(c)
    if a.inspect_current:
        if a.execute:
            raise ValueError('inspect and execute are separate actions')
        value = board.capture(c, before=True)
        print(json.dumps({'readonly': True, 'pm_entered': False, 'before': value, 'preflight_reasons': preflight(c, value)}))
        return 0
    os.umask(0o077)
    result = dispatch(c, board)
    print(json.dumps(result))
    return 0 if result['classification'] == 'evidence_collected' else 1


if __name__ == '__main__':
    raise SystemExit(main())

