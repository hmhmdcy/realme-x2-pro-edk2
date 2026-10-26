from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import sys

os.umask(0o077)
out = Path('/var/lib/samurai/k185-load')
out.mkdir(mode=0o700)
assert os.uname().version.startswith('#183 ')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k185-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert json.loads(Path('/var/lib/samurai/k185-scan-before-v2/result.json').read_text())['pass_all']
assert not subprocess.run(['pgrep', '-f', 'test-bluez-scan-preserve-pairs.py'], capture_output=True).stdout.strip()
candidate = Path('/var/lib/samurai/k185-tools/hci_uart-k185-private.ko')
report = json.loads(Path('/var/lib/samurai/k185-tools/module-build-validation.json').read_text())
assert hashlib.sha256(candidate.read_bytes()).hexdigest() == report['candidate_sha256']
expected = report['vermagic']
assert subprocess.check_output(['modinfo', '-F', 'vermagic', str(candidate)], text=True).strip() == expected
assert Path('/sys/module/hci_uart/refcnt').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)
before_log = subprocess.check_output(['dmesg'], text=True)
(out / 'dmesg-before-private.txt').write_text(before_log)
original = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/bluetooth/hci_uart.ko'
baseline = json.loads(Path('/var/lib/samurai/k185-baseline/summary.json').read_text())
assert hashlib.sha256(original.read_bytes()).hexdigest() == baseline['original_hci_uart_sha256']


def command(args, name, timeout=30):
    p = subprocess.run(args, capture_output=True, timeout=timeout)
    (out / (name + '-private.txt')).write_bytes(p.stdout + p.stderr)
    if p.returncode:
        raise RuntimeError('operation failed: ' + name)
    return p.stdout


stopped = False
try:
    command(['rc-service', 'bluetooth', 'stop'], 'service-stop')
    assert not subprocess.run(['pidof', 'bluetoothd'], capture_output=True).stdout.strip()
    command(['/usr/sbin/samurai-bluetooth', 'stop'], 'module-stop')
    stopped = True
    assert not Path('/sys/class/bluetooth/hci0').exists()
    for module in ['btbcm', 'btqca']:
        command(['insmod', str(original.parent / (module + '.ko'))], module + '-load')
    command(['insmod', str(candidate)], 'candidate-load')
    command(['rc-service', 'bluetooth', 'start'], 'service-start', timeout=35)
    counter = Path('/sys/kernel/debug/bluetooth/hci0/ibs/pulse_rx_nuls')
    assert counter.is_file() and counter.stat().st_mode & 0o222 == 0
    data = candidate.read_bytes()
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = data[headers[index][4]:headers[index][4] + headers[index][5]]
    notes = [row for row in headers if strings[row[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(notes) == 1
    note = notes[0]
    assert Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes() == data[note[4]:note[4] + note[5]]
    after_log = subprocess.check_output(['dmesg'], text=True)
    (out / 'dmesg-after-private.txt').write_text(after_log)
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    assert after_log.startswith(before_log)
    delta = after_log[len(before_log):]
    faults = {name: delta.count(value) for name, value in {
        'reassembly': 'Frame reassembly failed', 'warning': 'WARNING:', 'oops': 'Oops:',
        'gpu': 'gpu fault:', 'dpu': 'Frame done timeout', 'qca_setup': 'QCA Failed',
        'unknown_symbol': 'Unknown symbol'}.items()}
    assert not any(faults.values()), faults
    result = {'candidate_sha256': report['candidate_sha256'], 'loaded_build_id_matches_candidate': True,
              'counter_read_only': True, 'pulse_nuls': int(counter.read_text()),
              'delta_faults': faults, 'taint': 0, 'original_system_module_unchanged': True,
              'temporary_candidate_loaded': True, 'rollback_attempted': False}
    (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
except BaseException:
    (out / 'candidate-failed.txt').write_text('Candidate load/initialization failed; preserving diagnostics.\n')
    if stopped:
        subprocess.run(['rc-service', 'bluetooth', 'stop'], capture_output=True, timeout=25)
        subprocess.run(['/usr/sbin/samurai-bluetooth', 'stop'], capture_output=True, timeout=25)
        p = subprocess.run(['rc-service', 'bluetooth', 'start'], capture_output=True, timeout=35)
        (out / 'rollback-private.txt').write_bytes(p.stdout + p.stderr)
        (out / 'rollback-exit.txt').write_text(str(p.returncode) + '\n')
    raise
