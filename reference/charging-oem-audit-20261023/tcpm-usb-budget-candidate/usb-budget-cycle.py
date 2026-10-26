"""One software USB disconnect/reconnect during the existing bounded 508 trial.

The boot guard remains armed. No descriptor, supply limit, charging property,
role, PMIC register or diagnostic command is written. Host SSH return is a
separate acceptance condition; a successful sysfs write is never acceptance.
"""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback

ROOT = Path('/root/charging-management-20261023/tcpm508-trial-20261025-01')
RUN = ROOT / 'usb-budget-cycle-01'
UDC = Path('/sys/class/udc/a600000.usb')
VERSION = '#508 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'


def selected(value):
    if '[' in value:
        return value.split('[', 1)[1].split(']', 1)[0]
    return value.strip()


def budget_matches(row, value, configured):
    return (row['native_online'] == 1 and row['native_type'] == 'SDP'
            and row['native_max'] == row['native_input'] == value
            and row['tcpm_online'] == 1 and row['tcpm_type'] == 'C'
            and row['tcpm_max'] == row['tcpm_now'] == value
            and row['tcpm_voltage'] == 5000000
            and row['roles'] == dict(power_role='sink', data_role='device',
                                     power_operation_mode='default')
            and ((row['udc'] == 'configured') if configured
                 else (row['udc'] != 'configured')))


def exercise(read, write, now, sleep, record):
    """Always request reconnect, including a partial/failed disconnect write."""
    out = dict(passed=False, disconnect_observed=False, reconnect_observed=False,
               failure=None, reconnect_error=None)
    try:
        write('disconnect')
        until = now() + 5
        stable = None
        while now() < until:
            row = read()
            record('disconnected', row)
            if budget_matches(row, 0, False):
                if stable is None:
                    stable = now()
                elif now() - stable >= .25:
                    out['disconnect_observed'] = True
                    break
            else:
                stable = None
            sleep(.25)
        if not out['disconnect_observed']:
            raise RuntimeError('native/TCPM zero allowance was not observed')
    except BaseException:
        out['failure'] = traceback.format_exc()
    finally:
        try:
            write('connect')
        except BaseException:
            out['reconnect_error'] = traceback.format_exc()
    # Continue collecting recovery even if the disconnect predicate failed.
    until = now() + 25
    stable = None
    try:
        while now() < until:
            row = read()
            record('reconnecting', row)
            if budget_matches(row, 500000, True):
                if stable is None:
                    stable = now()
                elif now() - stable >= 1:
                    out['reconnect_observed'] = True
                    break
            else:
                stable = None
            sleep(.25)
    except BaseException:
        out['recovery_read_error'] = traceback.format_exc()
    out['passed'] = (out['disconnect_observed'] and out['reconnect_observed']
                     and not out['failure'] and not out['reconnect_error'])
    return out


def atomic_result(path, value):
    raw = (json.dumps(value, indent=2) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def recover(expected_boot):
    # Independent process, intentionally no PDEATHSIG: reconnect if the worker
    # exits before returning from its normal reconnect request. The original
    # boot guard is the final recovery if the USB path itself cannot recover.
    time.sleep(7)
    result = dict(boot=boot(), write_attempted=False, error=None)
    try:
        if boot() != expected_boot or os.uname().version != VERSION:
            result['reason'] = 'trial boot already ended'
        elif (RUN / 'reconnect-returned.json').exists():
            result['reason'] = 'worker reconnect request returned'
        elif (UDC / 'state').read_text().strip() == 'configured':
            result['reason'] = 'UDC already configured'
        else:
            result['write_attempted'] = True
            (UDC / 'soft_connect').write_text('connect\n')
            result['reason'] = 'independent reconnect request returned'
    except BaseException:
        result['error'] = traceback.format_exc()
    atomic_result(RUN / 'recovery-terminal.json', result)


def execute():
    assert os.geteuid() == 0 and not sys.flags.optimize
    assert os.uname().version == VERSION
    assert not (ROOT / 'accepted.json').exists()
    expected_boot = boot()
    spec = importlib.util.spec_from_file_location('cycle508_audit', ROOT / 'audit-phone.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    before = audit.audit()
    assert before['passed'], before
    state = json.loads((ROOT / 'state.json').read_bytes())
    assert state['event'] == 'watchdog-running' and state['boot'] == expected_boot
    # Reserve at least three minutes of the original guard window. No guard
    # acknowledgement, extension, restart, or concurrent rollback is permitted.
    assert 0 <= time.clock_gettime(time.CLOCK_BOOTTIME) - state['boottime'] <= 120
    assert (UDC / 'state').read_text().strip() == 'configured'
    gadget = Path('/sys/kernel/config/usb_gadget/samurai')
    assert (gadget / 'UDC').read_text().strip() == 'a600000.usb'
    assert (gadget / 'configs/c.1/MaxPower').read_text().strip() == '500'
    original_binding = (gadget / 'UDC').read_bytes()
    original_power = (gadget / 'configs/c.1/MaxPower').read_bytes()
    tcpm = next(p for p in Path('/sys/class/power_supply').iterdir()
                if p.name.startswith('tcpm-source-psy-'))
    port = Path('/sys/class/typec/port0')
    native = Path('/sys/class/power_supply/samurai-usb-input')
    os.umask(0o077)
    RUN.mkdir(mode=0o700)  # One shot. An existing run must be inspected.
    atomic_result(RUN / 'before.json', before)
    with (RUN / 'recovery.stdout').open('xb') as stdout, (RUN / 'recovery.stderr').open('xb') as stderr:
        helper = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()),
                                   '--recover', expected_boot], stdin=subprocess.DEVNULL,
                                  stdout=stdout, stderr=stderr, close_fds=True,
                                  start_new_session=True)
    proc = Path('/proc', str(helper.pid))
    fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    atomic_result(RUN / 'recovery-launch.json', dict(pid=helper.pid, startticks=int(fields[19])))
    started = time.clock_gettime(time.CLOCK_BOOTTIME)

    def read():
        assert boot() == expected_boot and os.uname().version == VERSION
        status = json.loads((ROOT / 'state.json').read_bytes())
        assert status['event'] == 'watchdog-running' and status['boot'] == expected_boot
        assert time.clock_gettime(time.CLOCK_BOOTTIME) - status['boottime'] < 240
        value = lambda path: path.read_text().strip()
        return dict(boottime=time.clock_gettime(time.CLOCK_BOOTTIME), udc=value(UDC / 'state'),
                    native_online=int(value(native / 'online')),
                    native_type=selected(value(native / 'usb_type')),
                    native_max=int(value(native / 'current_max')),
                    native_input=int(value(native / 'input_current_limit')),
                    tcpm_online=int(value(tcpm / 'online')), tcpm_type=selected(value(tcpm / 'usb_type')),
                    tcpm_max=int(value(tcpm / 'current_max')), tcpm_now=int(value(tcpm / 'current_now')),
                    tcpm_voltage=int(value(tcpm / 'voltage_now')),
                    roles={key: selected(value(port / key)) for key in
                           ['power_role', 'data_role', 'power_operation_mode']},
                    telemetry=value(Path('/sys/bus/i2c/devices/0-005c/telemetry')))

    def write(action):
        assert action in ['disconnect', 'connect'] and boot() == expected_boot
        (UDC / 'soft_connect').write_text(action + '\n')
        if action == 'connect':
            atomic_result(RUN / 'reconnect-returned.json', dict(boottime=time.clock_gettime(time.CLOCK_BOOTTIME)))

    with (RUN / 'samples.jsonl').open('x', buffering=1) as stream:
        def record(phase, row):
            stream.write(json.dumps(dict(phase=phase, **row)) + '\n')
        result = exercise(read, write, lambda: time.clock_gettime(time.CLOCK_BOOTTIME), time.sleep, record)
    result['phone_path_passed'] = result.pop('passed')
    result.update(passed=False, boot=expected_boot, software_disconnect_only=True, physical_detach_tested=False,
                  direct_budget_writes=0, automatic_rollback_acknowledged=False,
                  host_SSH_return_verified=False, duration_seconds=time.clock_gettime(time.CLOCK_BOOTTIME)-started)
    try:
        result['recovery_process_returncode'] = helper.wait(timeout=15)
        assert result['recovery_process_returncode'] == 0
        result['recovery'] = json.loads((RUN / 'recovery-terminal.json').read_bytes())
        assert not result['recovery']['error']
        result['after'] = audit.audit()
        assert result['after']['passed'], result['after']
        assert (gadget / 'UDC').read_bytes() == original_binding
        assert (gadget / 'configs/c.1/MaxPower').read_bytes() == original_power
        assert not (ROOT / 'accepted.json').exists()
    except BaseException:
        result['phone_path_passed'] = False
        result['postcheck_error'] = traceback.format_exc()
    atomic_result(RUN / 'result.json', result)
    print(json.dumps(result), flush=True)
    return 0 if result['phone_path_passed'] else 3


if __name__ == '__main__':
    if sys.argv[1:] == ['--execute']:
        raise SystemExit(execute())
    elif len(sys.argv) == 3 and sys.argv[1] == '--recover':
        recover(sys.argv[2])
    else:
        raise SystemExit('explicit --execute required; --recover is internal')
