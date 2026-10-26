#!/usr/bin/env python3
"""One coordinated native-server/Windows-central window; default is offline preflight."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
SERVER_SHA = 'a1f7c44c8e863bf1fcec9e9e507c4e9d621b0410b17e38b9750f76cae33c9004'
CENTRAL_SHA = '79620f7b837834601393d7238b2b17e1912218dfdfc6f4b46dcb8d81f541efc7'
PRIVATE_ROOT = Path('/mnt/e/edk2-samurai-out')
CENTRAL_PRIVATE_ROOT = PRIVATE_ROOT / 'bluetooth-windows-central-20261023'
SECONDS = 60
MINIMUM_REMAINING = 45


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def require_central_output(path):
    # The unchanged Windows executable validates both config and result under
    # this exact directory. Reject a mismatching output before launching SSH.
    require(path.is_absolute() and CENTRAL_PRIVATE_ROOT in path.resolve().parents,
            'Output must be inside the Windows central private directory')


def eligible(ready, elapsed):
    """Host monotonic budget is conservative: native setup starts after this host clock."""
    left = min(float(ready.get('remaining_seconds', 0)), SECONDS - elapsed)
    return bool(ready.get('registered') and not ready.get('stopping') and
                not ready.get('finished') and left >= MINIMUM_REMAINING)


def coordinate(server_call, ready_call, client_call, clock=time.monotonic):
    """Always await our bounded server, including readiness/client failure; no retries."""
    report = dict(windows_client_started=False, server_terminal=False)
    started = clock()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(server_call)
        try:
            ready = ready_call()
            elapsed = clock() - started
            report['ready'] = ready
            report['ready_elapsed_seconds'] = round(elapsed, 3)
            if future.done() or not eligible(ready, elapsed):
                report['client_not_started_reason'] = 'server_terminal_or_insufficient_confirmed_window'
            else:
                report['windows_client_started'] = True
                report['client_exit'] = client_call()
        except Exception as error:
            report['orchestration_error_type'] = type(error).__name__
        finally:
            try:
                report['server_exit'] = future.result()
                report['server_terminal'] = True
            except Exception as error:
                report['server_transport_error_type'] = type(error).__name__
                report['server_terminal'] = False
    return report


def preflight(args):
    require(sys.platform == 'linux', 'Run in the existing WSL Ubuntu environment')
    require_central_output(args.output)
    for path in [args.baseline, args.adoption, args.windows_probe, args.central_exe, args.output]:
        require(path.is_absolute() and PRIVATE_ROOT in path.resolve().parents,
                'Evidence, executable and output must stay in the private output root')
    require(not args.output.exists() and not args.output.is_symlink() and args.output.parent.is_dir(),
            'Output must be new with an existing parent')
    require(re.fullmatch(r'/var/lib/samurai/bt-le-[a-z0-9-]+', args.remote_output),
            'Use one new, explicit remote run directory')
    require(re.fullmatch('[0-9a-f]{64}', args.charging_manifest_sha256), 'Invalid manifest SHA256')
    require(0 <= time.time() - args.baseline.stat().st_mtime <= 180,
            'Need a fresh read-only baseline after the current device handoff')
    baseline = load(args.baseline)
    adoption = load(args.adoption)
    require(adoption.get('original_key_verified') and adoption.get('baseline440_verified'),
            'Original authenticated transport adoption missing')
    require(str(adoption.get('guard_path', '')).startswith('/var/lib/samurai/'), 'Invalid native boot guard')
    require(baseline.get('release') == RELEASE and baseline.get('taint') == '0' and
            baseline.get('elapsed_within_budget'), 'Baseline release, taint or completion mismatch')
    require(len(baseline.get('module_provenance', {})) == 3 and all(
        row.get('disk_is_expected_r0') and row.get('loaded_note_matches_disk')
        for row in baseline['module_provenance'].values()), 'Baseline Bluetooth modules differ')
    info = baseline.get('native_management_info', {}).get('info', {})
    require(info.get('le_supported') and info.get('le_enabled'), 'Native MGMT LE capability not established')
    require(baseline['files']['/usr/share/samurai-charging/manifest.json']['sha256'] ==
            args.charging_manifest_sha256, 'Current manifest differs from this handoff')
    require(baseline['charging']['mp2650-input'].get('health') == 'Good', 'Charging health not Good')
    objects = baseline['dbus']['objects']
    adapter = objects['/org/bluez/hci0']
    require(all(name in adapter for name in ['org.bluez.GattManager1', 'org.bluez.LEAdvertisingManager1']),
            'Native GATT/advertisement managers missing')
    require(not any(bool(obj.get('org.bluez.Device1', {}).get('Connected')) for obj in objects.values()),
            'Existing Bluetooth connection must remain idle')
    require(not any(bool(adapter['org.bluez.Adapter1'].get(name)) for name in
                    ['Powered', 'Discovering', 'Pairable', 'Discoverable']), 'Baseline adapter is not idle/off')
    require(int(adapter['org.bluez.LEAdvertisingManager1'].get('ActiveInstances', -1)) == 0,
            'Existing advertisement present or unknown')
    phone = str(adapter['org.bluez.Adapter1']['Address']).replace(':', '').upper()
    windows = str(load(args.windows_probe)['local_adapter_address_private']).upper()
    require(re.fullmatch('[0-9A-F]{12}', phone) and re.fullmatch('[0-9A-F]{12}', windows),
            'Exact private peer addresses missing')
    source_path = Path(__file__).resolve().parents[1] / 'bluetooth-le-peer-20261023/phone-gatt-peer.py'
    source = source_path.read_bytes()
    require(hashlib.sha256(source).hexdigest() == SERVER_SHA, 'Unreviewed native server source')
    require(hashlib.sha256(args.central_exe.read_bytes()).hexdigest() == CENTRAL_SHA,
            'Unreviewed Windows central executable')
    config = dict(expected_address=phone, server_window_confirmed=False, operation_timeout_ms=5000,
                  scan_timeout_ms=5000, total_timeout_seconds=30, short_sequence=1, long_sequence=2)
    peer = ':'.join(windows[i:i+2] for i in range(0, 12, 2))
    return source, adoption['guard_path'], peer, config


READY_SOURCE = '''from pathlib import Path
import json,time
p=Path(REMOTE_OUTPUT)
deadline=time.monotonic()+12
status=dict(registered=False,stopping=False,finished=False,remaining_seconds=0)
while time.monotonic()<deadline:
    events=p/'events-private.jsonl'
    try:
        rows=[json.loads(x) for x in events.read_text().splitlines()]
        age=time.time()-events.stat().st_mtime
        status=dict(registered=any(x['event']=='gatt_and_advertisement_registered' for x in rows),
            stopping=any(x['event']=='stopping' for x in rows),finished=(p/'summary-private.json').is_file(),
            remaining_seconds=round(WINDOW_SECONDS-(rows[-1]['elapsed_ms']/1000+age),2) if rows and age>=0 else 0)
    except (FileNotFoundError,json.JSONDecodeError):pass
    if status['registered'] or status['stopping'] or status['finished']:break
    time.sleep(.1)
print(json.dumps(status))
'''


def run(args, source, guard, peer, config):
    # Import only for explicit run; no transport query in offline preflight.
    from host import ssh
    result = ssh('test ! -e ' + shlex.quote(args.remote_output) + ' && test ! -L ' +
                 shlex.quote(args.remote_output), timeout=15, check=False)
    require(result.returncode == 0, 'Remote run directory exists or transport precheck failed')
    args.output.mkdir(mode=0o700)
    config_path = args.output / 'windows-config-private.json'
    result_path = args.output / 'windows-result-private.json'
    save(config_path, config)
    save(args.output / 'launch-spec-private.json', dict(remote_output=args.remote_output,
         server_source_sha256=SERVER_SHA, central_sha256=CENTRAL_SHA, guard_path=guard,
         charging_manifest_sha256=args.charging_manifest_sha256, explicit_window_confirmed=True))
    windows_paths = [subprocess.run(['wslpath', '-w', str(p)], capture_output=True, text=True,
                     timeout=5, check=True).stdout.strip() for p in [config_path, result_path]]
    native_args = ['timeout', '-s', 'TERM', '-k', '5', '105', 'python3', '-u', '-',
                   '--peer-address', peer, '--boot-guard-file', guard, '--charging-manifest-sha256',
                   args.charging_manifest_sha256, '--seconds', str(SECONDS), '--output', args.remote_output,
                   '--capture-backend', 'native-monitor']

    def server_call():
        try:
            result = ssh(' '.join(shlex.quote(x) for x in native_args), input=source, timeout=125, check=False)
        except subprocess.TimeoutExpired as error:
            (args.output / 'server-stdout-private.log').write_bytes(error.stdout or b'')
            (args.output / 'server-stderr-private.log').write_bytes(error.stderr or b'')
            raise
        (args.output / 'server-stdout-private.log').write_bytes(result.stdout)
        (args.output / 'server-stderr-private.log').write_bytes(result.stderr)
        return result.returncode

    def ready_call():
        query = READY_SOURCE.replace('REMOTE_OUTPUT', repr(args.remote_output)).replace('WINDOW_SECONDS', str(SECONDS))
        result = ssh('timeout -s TERM -k 2 16 python3 -', input=query.encode(), timeout=25, check=False)
        (args.output / 'ready-stdout-private.log').write_bytes(result.stdout)
        (args.output / 'ready-stderr-private.log').write_bytes(result.stderr)
        require(result.returncode == 0, 'Readiness query failed')
        return json.loads(result.stdout)

    def client_call():
        config['server_window_confirmed'] = True
        config_path.write_text(json.dumps(config, indent=2)+'\n')
        try:
            result = subprocess.run([str(args.central_exe), '--run', *windows_paths],
                                    capture_output=True, timeout=45)
        except subprocess.TimeoutExpired as error:
            (args.output / 'client-stdout-private.log').write_bytes(error.stdout or b'')
            (args.output / 'client-stderr-private.log').write_bytes(error.stderr or b'')
            save(args.output / 'client-timeout-private.json', dict(timeout_seconds=45,
                 windows_process_terminal_independently_verified=False))
            raise
        (args.output / 'client-stdout-private.log').write_bytes(result.stdout)
        (args.output / 'client-stderr-private.log').write_bytes(result.stderr)
        return result.returncode

    report = coordinate(server_call, ready_call, client_call)
    report['physical_disconnect_independently_verified'] = False
    report['recovery_requires_native_terminal_and_post_readback'] = True
    save(args.output / 'orchestration-private.json', report)
    # Deliberately omit identities and server/client raw records from public stdout.
    print(json.dumps({key: report.get(key) for key in ['windows_client_started', 'client_exit',
          'server_exit', 'server_terminal', 'orchestration_error_type', 'server_transport_error_type']}))
    return 0 if report.get('server_exit') == 0 and report.get('client_exit') == 0 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline', 'adoption', 'windows-probe', 'central-exe', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--remote-output', required=True)
    parser.add_argument('--charging-manifest-sha256', required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--window-confirmed', action='store_true')
    args = parser.parse_args()
    require(not args.run or args.window_confirmed, 'Explicit current coordinated device window required')
    inputs = preflight(args)
    if not args.run:
        print(json.dumps(dict(offline_preflight_passed=True, device_or_radio_accessed=False)))
        return 0
    return run(args, *inputs)


if __name__ == '__main__':
    sys.exit(main())
