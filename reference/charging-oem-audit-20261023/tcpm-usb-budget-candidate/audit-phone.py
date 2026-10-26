"""Read-only audit of one508 trial. Never acknowledge or change charging mode."""
from pathlib import Path
import fcntl, hashlib, importlib.util, json, os, re, subprocess, sys, time, traceback

ROOT = Path('/root/charging-management-20261023/tcpm508-trial-20261025-01')
VERSION = '#508 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
MANIFEST = 'c92f0a52c383919a2c7ca615ba1fad0ec09db10a87c941b5752b3fbcd9caaf76'
DT = Path('/sys/firmware/devicetree/base')
TC = DT / 'soc@0/spmi@c440000/pmic@2/typec@1500'
DWC = DT / 'soc@0/usb@a6f8800/usb@a600000'
NOTES = {
    'samurai_usb_input': '3c6247f14ff9f2ab23c149de814a66980dcc6d91c03c396f0101cb56781ee0fa',
    'samurai_mp2650': '1df00d554b85aa45d4bbbc0d1a6a7a4cbd56ba4da45ae48d54bb8ae1f3434d08',
    'samurai_gauge_protection': 'bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd',
}

def text(path):
    return Path(path).read_text().strip()

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def active(value):
    selected = re.findall(r'\[([^\]]+)\]', value)
    return selected[0] if len(selected) == 1 else value.strip()

def check_default_usb_budget(roles, tcpm_psy, native_ua):
    # This particular trial uses the existing computer SDP500 connection.
    # A stale100 or a separate PD contract must not pass the default-Rp fix.
    assert native_ua == 500000, 'requires the actual native SDP500 allowance'
    assert roles['power_operation_mode'] == 'default', 'not the default-Rp trial case'
    assert active(tcpm_psy['usb_type']) == 'C', 'PD is a separate contract case'
    assert tcpm_psy['online'] == '1' and int(tcpm_psy['voltage_now']) == 5000000
    assert int(tcpm_psy['current_max']) == native_ua, 'TCPM maximum differs from actual USB allowance'
    assert int(tcpm_psy['current_now']) == native_ua, 'TCPM operating limit differs from actual USB allowance'
    return dict(default_Rp_non_PD=True, native_allowance_ua=native_ua,
                tcpm_maximum_and_operating_limit_equal=True)


def sample():
    result = subprocess.run(['/usr/sbin/samurai-charging', 'status'], capture_output=True, text=True, timeout=12)
    assert result.returncode == 0, result.stderr
    managed = json.loads(result.stdout)
    assert managed['managed']
    s = managed['sample']
    assert s['shadow'] == 0 and s['valid'] == s['online'] == s['protection_ok'] == 1
    assert 0 <= s['age_ms'] <= 3000
    assert all(s[k] == 0 for k in ['latched', 'stop_error', 'error', 'fault', 'thermal_inhibit', 'cycle_timeout', 'source_inhibit'])
    assert 100 <= s['temp_decic'] < 400
    assert min(s['cell1_uv'], s['cell2_uv']) >= 3500000 and max(s['cell1_uv'], s['cell2_uv']) <= 4375000
    psy = Path('/sys/class/power_supply')
    read = lambda n, k: text(psy/n/k)
    assert read('samurai-usb-input', 'online') == '1'
    assert '[SDP]' in read('samurai-usb-input', 'usb_type')
    assert read('samurai-usb-input', 'current_max') == '500000'
    caps = {k: int(read('mp2650-input', k)) for k in ['input_current_limit', 'constant_charge_current', 'constant_charge_voltage']}
    assert caps == dict(input_current_limit=500000, constant_charge_current=250000, constant_charge_voltage=8725000)
    assert read('mp2650-input', 'health') == read('samurai-gauge-protection', 'health') == 'Good'
    assert active(read('mp2650-input', 'charge_behaviour')) == 'auto'
    protection = {k: int(v, 0) for k, v in (word.split('=', 1) for word in text('/sys/devices/platform/samurai-gauge-protection/protection_state').split())}
    assert protection['id'] == 0x2719 and protection['safety'] == protection['pf'] == protection['error'] == 0
    return dict(boottime=time.clock_gettime(time.CLOCK_BOOTTIME), sample=s, caps=caps, protection=protection)

def audit(check_carriers=False):
    report = dict(passed=False, accepted=False, read_only=True, version=os.uname().version,
                  full_PD_contract_verified=False, physical_detach_tested=False,
                  MAC_query_or_rearm=False)
    try:
        assert os.geteuid() == 0 and not sys.flags.optimize
        assert os.uname().version == VERSION and os.uname().release == RELEASE, 'requires exact507 kernel'
        spec = importlib.util.spec_from_file_location('readonly507_guard_definitions', ROOT/'new/usr/lib/samurai-charging/tcpm508-boot-guard.py')
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        meta = guard.load()
        assert guard.boot() != meta['source_boot']
        assert json.loads((ROOT/'stage-result.json').read_bytes())['passed']
        assert not (ROOT/'accepted.json').exists(), 'trial must retain its automatic rollback'
        state = json.loads((ROOT/'state.json').read_bytes())
        assert state['event'] == 'watchdog-running' and state['boot'] == guard.boot()
        assert 0 <= time.clock_gettime(time.CLOCK_BOOTTIME)-state['boottime'] < 240
        pid = int(state['pid'])
        proc = Path('/proc', str(pid))
        fields = (proc/'stat').read_text().rsplit(')', 1)[1].split()
        assert fields[0] != 'Z'
        argv = (proc/'cmdline').read_bytes().split(b'\0')
        assert str(ROOT/'new/usr/lib/samurai-charging/tcpm508-boot-guard.py').encode() in argv
        assert b'watch' in argv
        environ = (proc/'environ').read_bytes().split(b'\0')
        lock_fd = next(int(x.split(b'=', 1)[1]) for x in environ if x.startswith(b'IMAGE505_LOCK_FD='))
        assert (proc/'fd'/str(lock_fd)).resolve(strict=True) == ROOT/'watchdog.lock'
        fd = os.open(ROOT/'watchdog.lock', os.O_RDONLY | os.O_NOFOLLOW)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
                raise RuntimeError('watchdog recovery lock is not held')
        finally:
            os.close(fd)
        report['watchdog'] = dict(pid=pid, startticks=int(fields[19]), process_live=True, lock_held=True)
        assert int(text('/proc/sys/kernel/tainted')) == 4096
        for path, row in meta['files'].items():
            assert guard.target_hash(path) == row['new']['sha256'], path
        assert sha('/usr/share/samurai-charging/manifest.json') == MANIFEST
        for name, expected in NOTES.items():
            assert text('/sys/module/'+name+'/initstate') == 'live'
            assert sha('/sys/module/'+name+'/notes/.note.gnu.build-id') == expected
        assert not (TC/'realme,pd5v-only').exists()
        assert (TC/'power-supplies').read_bytes() == bytes.fromhex('0000015d')
        assert (DT/'soc@0/spmi@c440000/pmic@2/usb-input@1300/phandle').read_bytes() == bytes.fromhex('0000015d')
        assert (TC/'connector/power-role').read_bytes() == b'sink\0'
        assert (TC/'connector/data-role').read_bytes() == b'device\0'
        assert (TC/'connector/sink-pdos').read_bytes() == bytes.fromhex('04019032')
        assert (DT/'soc@0/eud-off-route/status').read_bytes() == b'disabled\0'
        assert all(not (DWC/k).exists() for k in ['samurai,apsd-owner', 'samurai,apsd-pd5v-bridge', 'samurai,apsd-typec', 'samurai,apsd-eud-route'])
        driver = Path('/sys/bus/platform/drivers/qcom,pmic-typec/c440000.spmi:pmic@2:typec@1500')
        assert driver.is_symlink()
        ports = [q for q in Path('/sys/class/typec').iterdir() if re.fullmatch(r'port[0-9]+', q.name)]
        assert len(ports) == 1
        port = ports[0]
        assert port.resolve().is_relative_to(driver.resolve())
        assert (port.parent/(port.name+'-partner')).exists()
        roles = {k: text(port/k) for k in ['power_role', 'data_role', 'power_operation_mode']}
        report['roles'] = roles
        assert active(roles['power_role']) == 'sink' and active(roles['data_role']) == 'device'
        psys = [q for q in Path('/sys/class/power_supply').iterdir() if q.name.startswith('tcpm-source-psy-')]
        assert len(psys) == 1
        assert psys[0].resolve().is_relative_to(driver.resolve())
        tcpm_psy = {k: text(psys[0]/k) for k in ['online', 'usb_type', 'voltage_now', 'current_max', 'current_now']}
        report['tcpm_power_supply'] = tcpm_psy
        report['before'] = sample()
        native_ua = int(text('/sys/class/power_supply/samurai-usb-input/current_max'))
        report['budget_before'] = check_default_usb_budget(roles, tcpm_psy, native_ua)
        time.sleep(2)
        report['after'] = sample()
        roles_after = {k: text(port/k) for k in ['power_role', 'data_role', 'power_operation_mode']}
        tcpm_after = {k: text(psys[0]/k) for k in ['online', 'usb_type', 'voltage_now', 'current_max', 'current_now']}
        report.update(roles_after=roles_after, tcpm_power_supply_after=tcpm_after)
        assert active(roles_after['power_role']) == 'sink' and active(roles_after['data_role']) == 'device'
        native_after = int(text('/sys/class/power_supply/samurai-usb-input/current_max'))
        report['budget_after'] = check_default_usb_budget(roles_after, tcpm_after, native_after)
        kmsg = subprocess.run(['dmesg'], capture_output=True, text=True, check=True).stdout
        assert not any(word in kmsg for word in ['BUG:', 'WARNING: CPU:', 'Oops:', 'Unknown symbol', 'disagrees about version'])
        report['typec_log'] = [line for line in kmsg.splitlines() if 'typec' in line.lower() or 'tcpm' in line.lower()]
        if check_carriers:
            for name in ['boot', 'logdump']:
                assert guard.digest(guard.PARTS[name][0]) == meta['parts'][name]['new']
            report['both_carrier_hashes_verified'] = True
        report.update(passed=True, fixed_sink_registered=True, partner_attached=True, native_USB500_and_caps_preserved=True,
                      automatic_rollback_still_armed=True, boot_id=guard.boot())
    except BaseException as error:
        report['error'] = repr(error)
        report['traceback'] = traceback.format_exc()
    return report

if __name__ == '__main__':
    assert sys.argv[1:] in [[], ['--carriers']]
    result = audit(sys.argv[1:] == ['--carriers'])
    print(json.dumps(result))
    raise SystemExit(0 if result['passed'] else 3)
