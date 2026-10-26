"""Exercise real lifecycle functions without any handset hardware writes."""
from pathlib import Path
import importlib.util
import json
import tempfile
from unittest.mock import patch

path = Path(__file__).resolve().parents[2] / 'linux-port/ssc/samurai-ssc.py'
spec = importlib.util.spec_from_file_location('service', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
checks = 0


def rejected(fn, match):
    global checks
    try:
        fn()
    except RuntimeError as error:
        assert match in str(error), str(error)
    else:
        raise AssertionError('Expected refusal: ' + match)
    checks += 1


with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    m.CONTROL = root / 'control'; m.CONTROL.mkdir()
    m.BOOT = root / 'boot'; m.BOOT.write_text('current')
    node = root / 'node'; node.mkdir()
    m.POWER = root / 'power'; m.POWER.write_text('vdd=0 vddio=0')
    (node / 'state').write_text('offline')
    m.DAEMON = Path('/usr/libexec/samurai-hexagonrpcd')
    record = dict(boot_id='current', started=False, attempted=True,
                  original_firmware='original', original_recovery='enabled')
    with patch.object(m, 'write_node', side_effect=AssertionError('Unexpected hardware write')):
        rejected(lambda: m.start({}, record, node), 'already attempted')
        rejected(lambda: m.start({'skip_boot_id': 'current'}, {}, node), 'reboot required')
        rejected(lambda: m.stop(dict(record, boot_id='stale'), node), 'different boot')
        m.stop({}, node); checks += 1
        (node / 'state').write_text('running')
        rejected(lambda: m.stop({}, node), 'another service')
    events = []
    live = [True]

    def write(dest, value):
        events.append((dest.name, value))
        if dest == node / 'state':
            dest.write_text('offline')
        elif dest == m.POWER:
            dest.write_text('vdd=0 vddio=0')
        else:
            dest.write_text(value)

    def kill(pid, sig):
        assert pid == 123
        events.append(('signal', sig.name))
        live[0] = False

    m.POWER.write_text('vdd=1 vddio=1')
    with patch.object(m, 'owned_process', side_effect=lambda r: live[0]), \
         patch.object(m, 'write_node', side_effect=write), patch.object(m.os, 'kill', side_effect=kill):
        m.stop(dict(record, pid=123), node)
    assert events == [('state', 'stop'), ('signal', 'SIGTERM'), ('power', '0'),
                      ('firmware', 'original'), ('recovery', 'enabled')]
    assert json.loads((m.CONTROL / 'state.json').read_text())['stopped']
    checks += 2
    events.clear(); (node / 'state').write_text('running'); m.POWER.write_text('vdd=1 vddio=1')
    with patch.object(m, 'write_node', side_effect=lambda p,v: events.append((p.name,v))), \
         patch.object(m.os, 'kill', side_effect=AssertionError('Daemon killed before DSP offline')):
        rejected(lambda: m.stop(dict(record, pid=123), node), 'DSP not offline')
    assert events == [('state', 'stop')] and m.text(m.POWER) == 'vdd=1 vddio=1'
    checks += 1
    (node / 'state').write_text('offline')
    with patch.object(m, 'owned_process', return_value=False), \
         patch.object(m, 'write_node', side_effect=write), \
         patch.object(m.os, 'kill', side_effect=AssertionError('Reused PID signalled')):
        m.stop(dict(record, pid=123), node)
    checks += 1
    wanted = dict(pid=123, start_ticks=100, exe=str(m.DAEMON),
                  cmdline=[bytes(m.DAEMON), b'-f', b'/dev/fastrpc-sdsp', b'-d', b'sdsp',
                           b'-R', bytes(m.CONTROL / 'root'), b'-s'])
    for change, expected in [({}, True), ({'start_ticks':101}, False),
                             ({'exe':'/other'}, False), ({'cmdline':[b'other']}, False)]:
        with patch.object(m, 'process_identity', return_value=dict(wanted, **change)):
            assert m.owned_process(dict(pid=123, start_ticks=100)) is expected
            checks += 1
    with patch.object(m, 'process_identity', return_value=None):
        assert not m.owned_process(dict(pid=123, start_ticks=100)); checks += 1

receipt = dict(policy_checks=checks, real_lifecycle_functions_used=True,
               hardware_writes_performed=False, native_boot_verified=False)
(Path(__file__).resolve().parent / 'service-policy-validation.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
