"""One guarded unbound-lab replacement, observing the automatic rear probe."""
from pathlib import Path
import hashlib
import json
import os
import re
import stat
import struct
import subprocess
import tempfile
import time
import traceback

os.umask(0o077)
root = Path('/var/lib/samurai')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k236-runtime/boot-id-private.txt').read_bytes()
out = root / 'k236-lab-fix'
assert not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
state = dict(stage=236, state='running', phase='preflight', pid=os.getpid(),
             start_ticks=Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19])
trace = None
trace_removed = False
old_unloaded = False
new_attempt_started = False
error = None
report = None
sha = lambda data: hashlib.sha256(data).hexdigest()
def save(phase=None):
    if phase:
        state['phase'] = phase
    temp = out / 'state-next-private.json'
    temp.write_text(json.dumps(state, indent=2) + '\n')
    os.replace(temp, out / 'state-private.json')
def checked(args, label, timeout=30):
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    (out / (label + '-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, label
    return result
def note(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = data[sections[index][4]:sections[index][4] + sections[index][5]]
    found = [data[s[4]:s[4]+s[5]] for s in sections if strings[s[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(found) == 1
    return found[0]
def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
def atomic(path, data, mode=0o644, uid=0, gid=0):
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.k236-', dir=path.parent)
    temp = Path(name)
    try:
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(data)
                stream.flush()
            os.fchmod(fd, mode)
            os.fchown(fd, uid, gid)
            os.fsync(fd)
        finally:
            os.close(fd)
        assert temp.read_bytes() == data
        os.replace(temp, path)
        sync_directory(path.parent)
    finally:
        if temp.exists():
            temp.unlink()
def regulator_snapshot(parent):
    result = {}
    for node in Path('/sys/class/regulator').glob('regulator.*'):
        if parent.resolve() not in node.resolve().parents:
            continue
        name = (node / 'name').read_text().strip()
        fields = {}
        for field in ['state', 'num_users', 'microvolts']:
            try:
                fields[field] = (node / field).read_text().strip()
            except OSError as failure:
                fields[field] = 'errno:' + str(failure.errno)
        result[name] = fields
    return result
def faults(log):
    return {name: log.count(needle) for name, needle in dict(warning=b'WARNING:', oops=b'Oops:',
        gpu=b'gpu fault:', fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
save()
try:
    assert json.loads((root / 'k236-runtime/state-private.json').read_text())['state'] == 'terminal'
    assert json.loads((root / 'k236-runtime/state-private.json').read_text())['exit_code'] == 1
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    tree = Path('/usr/lib/modules') / os.uname().release
    relative = 'kernel/drivers/regulator/qcom-pm8008-imx319-lab.ko'
    target = tree / relative
    candidate = root / 'k236-tools/qcom-pm8008-imx319-lab-fix.ko'
    lock = json.loads((root / 'k236-tools/lab-fix-lock-private.json').read_text())
    original = target.read_bytes()
    assert sha(original) == lock['old_sha256'] == '22c28914419c2be32d58967c0bbe73f0b2ccfb3ab074dda8830e6619b2f643fc'
    assert sha(candidate.read_bytes()) == lock['new_sha256']
    loaded_note = Path('/sys/module/qcom_pm8008_imx319_lab/notes/.note.gnu.build-id')
    assert loaded_note.read_bytes() == note(original)
    assert Path('/sys/module/qcom_pm8008_imx319_lab/refcnt').read_text().strip() == '0'
    inventory = {str(path.relative_to(tree)): sha(path.read_bytes()) for path in tree.rglob('*') if path.is_file()}
    assert inventory == json.loads((root / 'k236-baseline/module-inventory-private.json').read_text())
    assert len(inventory) == 789 and sum(name.endswith('.ko') for name in inventory) == 775
    q = Path('/sys/bus/i2c/devices/1-0004')
    p = Path('/sys/bus/i2c/devices/1-0008')
    for node in [q, p]:
        assert (node / 'driver').resolve().name == 'pm8008'
    assert Path('/sys/bus/platform/devices/camera-pmic-resets/driver').resolve().name == 'rmx1931-pm8008-resets'
    children = [node for node in Path('/sys/bus/platform/devices').iterdir() if p.resolve() in node.resolve().parents]
    assert len(children) == 1 and children[0].name.startswith('pm8008-reg-lab14.')
    child = children[0]
    assert not (child / 'driver').is_symlink() and not regulator_snapshot(p)
    rear = Path('/sys/bus/i2c/devices/7-0010')
    front = Path('/sys/bus/i2c/devices/9-0010')
    assert (rear / 'of_node/compatible').read_bytes() == b'realme,rmx1931-imx319\0'
    assert not (rear / 'driver').is_symlink()
    assert (front / 'driver').resolve().name == 'imx471'
    assert (front / 'power/runtime_status').read_text().strip() == 'suspended'
    q_before = regulator_snapshot(q)
    assert len(q_before) == 7 and all(values['state'] == 'disabled' and values['num_users'] == '0' for values in q_before.values())
    retained_notes = {name: Path('/sys/module', name, 'notes/.note.gnu.build-id').read_bytes()
                      for name in ['qcom_pm8008', 'qcom_pm8008_regulator', 'reset_realme_rmx1931_pm8008', 'imx471', 'qcom_camss', 'imx319']}
    before_log = subprocess.check_output(['dmesg'])
    assert not any(faults(before_log).values())
    (out / 'dmesg-before-private.txt').write_bytes(before_log)
    backup = out / 'before'
    backup.mkdir(mode=0o700)
    saved = {}
    for name in [n for n in inventory if not n.endswith('.ko')] + [relative]:
        path = tree / name
        dest = backup / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
        metadata = path.stat()
        saved[name] = dict(mode=stat.S_IMODE(metadata.st_mode), uid=metadata.st_uid, gid=metadata.st_gid)
    (out / 'saved-file-metadata-private.json').write_text(json.dumps(saved, indent=2) + '\n')
    trace = Path('/sys/kernel/tracing/instances/k236_lab_probe')
    assert not trace.exists()
    trace.mkdir()
    (trace / 'tracing_on').write_text('0')
    (trace / 'events/enable').write_text('0')
    (trace / 'buffer_size_kb').write_text('128')
    (trace / 'trace_clock').write_text('mono')
    selected = {}
    for event in ['i2c_write', 'i2c_read', 'i2c_reply']:
        node = trace / 'events/i2c' / event
        form = (node / 'format').read_text()
        (out / (event + '-format-private.txt')).write_text(form)
        assert 'adapter_nr;' in form
        assert all(field + ';' in form for field in ['addr', 'msg_nr', 'len', 'flags'])
        direction = 0 if event == 'i2c_write' else 1
        expression = 'adapter_nr == 7 && addr == 16 && msg_nr == %d && len == 2 && flags == %d' % (direction, direction)
        (node / 'filter').write_text(expression)
        assert 'parse_error' not in (node / 'filter').read_text()
        (node / 'enable').write_text('1')
        selected[event] = expression
    (out / 'trace-filters-private.json').write_text(json.dumps(selected, indent=2) + '\n')
    (trace / 'tracing_on').write_text('1')
    save('trace_armed_before_unbound_module_replacement')
    checked(['rmmod', 'qcom_pm8008_imx319_lab'], 'unload-unbound-lab')
    old_unloaded = True
    assert not Path('/sys/module/qcom_pm8008_imx319_lab').exists() and not (child / 'driver').is_symlink()
    atomic(target, candidate.read_bytes(), **saved[relative])
    checked(['depmod', '-a', os.uname().release], 'depmod', timeout=45)
    assert sha(target.read_bytes()) == lock['new_sha256']
    actual = {str(path.relative_to(tree)): sha(path.read_bytes()) for path in tree.rglob('*') if path.is_file()}
    expected_ko = {name: digest for name, digest in inventory.items() if name.endswith('.ko')}
    expected_ko[relative] = lock['new_sha256']
    assert {name: digest for name, digest in actual.items() if name.endswith('.ko')} == expected_ko
    assert len(actual) == 789
    (out / 'module-inventory-after-private.json').write_text(json.dumps(actual, indent=2) + '\n')
    (out / 'module-tree-after.sha256').write_text(''.join(digest + '  ' + name + '\n' for name, digest in sorted(actual.items())))
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    # The observer/trace already owns this phase before binding can trigger rear.
    save('before_new_lab_load_and_automatic_deferred_probe')
    new_attempt_started = True
    checked(['modprobe', 'qcom_pm8008_imx319_lab'], 'load-fixed-lab')
    assert loaded_note.read_bytes() == note(candidate.read_bytes())
    deadline = time.monotonic() + 25
    observations = []
    while True:
        rails = regulator_snapshot(p)
        observation = dict(lab_bound=(child / 'driver').is_symlink(), rear_bound=(rear / 'driver').is_symlink(),
                           rear_runtime=(rear / 'power/runtime_status').read_text().strip(), rails=rails)
        observations.append(observation)
        (out / 'probe-observations-private.json').write_text(json.dumps(observations, indent=2) + '\n')
        state['latest_observation'] = observation
        save('observing_automatic_probe_and_suspend')
        if (observation['lab_bound'] and observation['rear_bound'] and observation['rear_runtime'] == 'suspended' and
                set(rails) == {'cam-rear-vana', 'cam-rear-vdig'} and all(values['state'] == 'disabled' and values['num_users'] == '0' for values in rails.values())):
            break
        assert time.monotonic() < deadline, 'Fixed-lab/rear probe or autosuspend did not complete; preserve attempt'
        time.sleep(.2)
    assert (rear / 'driver').resolve().name == 'imx319'
    assert rails['cam-rear-vana']['microvolts'] == '2800000' and rails['cam-rear-vdig']['microvolts'] == '1104000'
    assert regulator_snapshot(q) == q_before
    assert all(Path('/sys/module', name, 'notes/.note.gnu.build-id').read_bytes() == value for name, value in retained_notes.items())
    assert all((node / 'driver').resolve().name == 'pm8008' for node in [p, q])
    assert (front / 'power/runtime_status').read_text().strip() == 'suspended'
    clocks = Path('/sys/kernel/debug/clk/clk_summary').read_text()
    for name in ['cam_cc_mclk1_clk', 'cam_cc_mclk2_clk']:
        rows = [line.split() for line in clocks.splitlines() if line.split() and line.split()[0] == name]
        assert len(rows) == 1 and int(rows[0][1]) == 0
    report = dict(stage=236, same236_boot=True, unbound_lab_only_replaced=True, old_lab_refcount_zero_verified=True,
                  parent_mfd_q_provider_and_front_notes_unchanged=True, new_lab_sha256=lock['new_sha256'],
                  p_l1_l4_only_registered=True, imx319_probe_identity_passed=True, rear_auto_suspended=True,
                  rear_rails_off_users0=True, rear_voltage_values_exact=True, q_all_seven_states_voltages_unchanged=True,
                  front_suspended=True, mclk1_mclk2_disabled=True, no_scene_capture=True,
                  no_mfd_provider_q_unbind_reset_or_reboot=True)
except BaseException:
    error = traceback.format_exc()
    (out / 'failure-private.txt').write_text(error)
    if old_unloaded and not new_attempt_started:
        # No new power probe occurred. Restore files; leave the unbound driver unloaded.
        recovery_errors = []
        for name, metadata in saved.items():
            try:
                atomic(tree / name, (backup / name).read_bytes(), **metadata)
            except BaseException as recovery_error:
                recovery_errors.append(type(recovery_error).__name__)
        (out / 'preload-file-recovery-private.json').write_text(json.dumps(dict(errors=recovery_errors, old_module_left_unloaded=True)) + '\n')
finally:
    if trace is not None and trace.exists():
        try:
            (trace / 'tracing_on').write_text('0')
            data = (trace / 'trace').read_bytes()
            (out / 'i2c-trace-private.txt').write_bytes(data)
            stats = {path.parent.name: path.read_text() for path in (trace / 'per_cpu').glob('cpu*/stats')}
            (out / 'trace-stats-private.json').write_text(json.dumps(stats, indent=2) + '\n')
            for node in (trace / 'events/i2c').iterdir():
                if (node / 'enable').exists():
                    (node / 'enable').write_text('0')
            trace.rmdir()
            trace_removed = True
        except BaseException:
            (out / 'trace-cleanup-failure-private.txt').write_text(traceback.format_exc())
            error = error or 'Trace cleanup failed'
    after = subprocess.check_output(['dmesg'])
    (out / 'dmesg-after-private.txt').write_bytes(after)
    for name, path in [('gpio', '/sys/kernel/debug/gpio'), ('regulators', '/sys/kernel/debug/regulator/regulator_summary'),
                       ('clocks', '/sys/kernel/debug/clk/clk_summary'), ('domains', '/sys/kernel/debug/pm_genpd/pm_genpd_summary')]:
        (out / (name + '-after-private.txt')).write_text(Path(path).read_text())
    final_faults = faults(after)
    if report is not None:
        report.update(trace_instance_removed=trace_removed, fault_counts=final_faults,
                      taint=int(Path('/proc/sys/kernel/tainted').read_text()))
        if any(final_faults.values()) or report['taint'] != 0:
            error = error or 'Kernel fault after probe'
        (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    state.update(state='terminal', phase='failed' if error else 'verified', exit_code=1 if error else 0,
                 trace_instance_removed=trace_removed, new_load_attempted=new_attempt_started)
    save()
if error:
    raise RuntimeError('Lab-fix attempt failed; inspect the retained native context')
