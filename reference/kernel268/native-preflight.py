from pathlib import Path
import hashlib, json, os, stat, subprocess
os.umask(63)
root = Path('/var/lib/samurai')
stage = root / 'k268-r19-package-candidates'
out = root / 'k268-r19-package-transaction'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (root / 'k267-work/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert Path('/lib/apk/db/installed').read_bytes() == (root / 'k268-tools/installed-before-private.txt').read_bytes()
assert not out.exists()
out.mkdir(mode=448)
old = json.loads((root / 'k239-r15-package-candidates/forward-manifest.json').read_text())
new = json.loads((stage / 'forward-manifest.json').read_text())
assert {p['name'] for p in old['packages']} == {p['name'] for p in new['packages']}
for package in old['packages']:
    for relative, item in package['files'].items():
        p = Path('/') / relative
        if item['kind'] == 'symlink':
            assert p.is_symlink() and os.readlink(p) == item['target']
        else:
            assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'] and stat.S_IMODE(p.stat().st_mode) == item['mode']
repositories = {}
for p in [Path('/etc/apk/repositories'), *sorted(Path('/etc/apk/repositories.d').glob('*'))]:
    if p.is_file():
        repositories[str(p)] = dict(bytes=p.read_bytes().hex(), mode=stat.S_IMODE(p.stat().st_mode))
(out / 'repositories-before-private.json').write_text(json.dumps(repositories, indent=2) + '\n')
(out / 'world-before-private.txt').write_bytes(Path('/etc/apk/world').read_bytes())
(out / 'installed-before-private.txt').write_bytes(Path('/lib/apk/db/installed').read_bytes())
(out / 'config-before-private.yaml').write_bytes(Path('/etc/libcamera/configuration.yaml').read_bytes())
assert sum((l.startswith('P:') for l in Path('/lib/apk/db/installed').read_text().splitlines())) == 961
repo = Path('/etc/apk/repositories.d/60-samurai-camera.list')
assert repo.exists() and 'k239-r15-package-candidates/forward/packages.adb' in repo.read_text()
repos = out / 'candidate-repositories.list'
repos.write_text('ndx file://' + str(stage / 'forward/packages.adb') + '\n')
p = subprocess.run(['apk', '--no-network', '--repositories-file', str(repos), 'add', '--simulate', 'samurai-camera-stack=0.1.0-r14'], capture_output=True, text=True, timeout=30)
(out / 'native-forward-dry-private.log').write_text(p.stdout + p.stderr)
assert p.returncode == 0
actions = [line for line in p.stdout.splitlines() if line.startswith('(')]
assert len(actions) == 7
for package in new['packages']:
    previous = '0.1.0-r10' if package['name'].startswith('samurai-camera-') else '99990.7.2-r15'
    assert any(('Upgrading ' + package['name'] + ' (' + previous + ' -> ' + package['version'] + ')' in line for line in actions))
assert not any(('Installing ' in l or 'Purging ' in l or 'Removing ' in l for l in actions))
assert Path('/lib/apk/db/installed').read_bytes() == (out / 'installed-before-private.txt').read_bytes()
report = dict(stage=268, native_phone_solver_passed=True, exactly_seven_camera_upgrades_no_additions_or_removals=True, all_current_camera_payloads_match_r15_rollback=True, current_961_package_database_world_repositories_and_configuration_saved=True, signed_repositories_only=True, same_current267_boot=True, package_transaction_not_sent=True)
(out / 'preflight-summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
