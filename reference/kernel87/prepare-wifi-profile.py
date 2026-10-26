from pathlib import Path
import hashlib, json, os, re, subprocess, tarfile

K = Path('/home/cy122/x2pro-linux/linux')
O = Path('/mnt/e/edk2-samurai-out/kernel87')
W = Path('/mnt/e/RealmeX2Pro edk2')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tracked = ['.config', 'include/config/auto.conf', 'include/generated/autoconf.h',
           'usr/initramfs_data.cpio', 'arch/arm64/boot/Image',
           'arch/arm64/boot/dts/qcom/sm8150-samurai.dts']
before = {p: sha(K / p) for p in tracked}
baseline = (K / '.config').read_text()
fragment = (W / 'reference/kernel87/wifi-prerequisites.config').read_text()
requested = dict(re.findall(r'^CONFIG_(\w+)=(\w+)$', fragment, re.M))
candidate = O / 'wifi-candidate.config'
assert not candidate.exists()
lines = [line for line in baseline.splitlines()
         if not any(line.startswith('CONFIG_' + symbol + '=') or
                    line == '# CONFIG_' + symbol + ' is not set'
                    for symbol in requested)]
candidate.write_text('\n'.join(lines) + '\n' + fragment)
env = os.environ.copy()
env.update(ARCH='arm64', SRCARCH='arm64', srctree=str(K),
           CC='aarch64-linux-gnu-gcc', LD='aarch64-linux-gnu-ld',
           NM='aarch64-linux-gnu-nm', OBJCOPY='aarch64-linux-gnu-objcopy',
           STRIP='aarch64-linux-gnu-strip', READELF='aarch64-linux-gnu-readelf',
           RUSTC='rustc', BINDGEN='bindgen', PAHOLE='pahole',
           KCONFIG_CONFIG=str(candidate),
           KCONFIG_AUTOCONFIG=str(O / 'wifi-auto.conf'),
           KCONFIG_AUTOHEADER=str(O / 'wifi-autoconf.h'),
           KCONFIG_RUSTCCFG=str(O / 'wifi-rustc_cfg'))
env['CC_VERSION_TEXT'] = subprocess.check_output(['aarch64-linux-gnu-gcc', '--version'], text=True).splitlines()[0]
env['RUSTC_VERSION_TEXT'] = subprocess.run(['bash', '-c', 'rustc --version 2>/dev/null || true'], capture_output=True, text=True).stdout.strip()
version = subprocess.run([str(K / 'scripts/pahole-version.sh'), 'pahole'], capture_output=True, text=True)
env['PAHOLE_VERSION'] = version.stdout.strip() if version.returncode == 0 else '0'
result = subprocess.run([str(K / 'scripts/kconfig/conf'), '--olddefconfig', str(K / 'Kconfig')],
                        cwd=K, env=env, capture_output=True, text=True)
(O / 'wifi-kconfig.log').write_text(result.stdout + result.stderr)
assert result.returncode == 0, result.stderr
resolved = dict(re.findall(r'^CONFIG_(\w+)=(.+)$', candidate.read_text(), re.M))
assert all(resolved.get(k, 'n') == v for k, v in requested.items()), requested
assert before == {p: sha(K / p) for p in tracked}
old = dict(re.findall(r'^CONFIG_(\w+)=(.+)$', baseline, re.M))
changed = {k: {'before': old.get(k, 'n'), 'candidate': resolved.get(k, 'n')}
           for k in sorted(old.keys() | resolved.keys()) if old.get(k) != resolved.get(k)}
assert not any(k in changed for k in ['RELR', 'TOOLS_SUPPORT_RELR', 'CC_VERSION_TEXT',
                                     'ARM64', 'INITRAMFS_SOURCE', 'USB_CONFIGFS_NCM'])
assert 'warning:' not in (O / 'wifi-kconfig.log').read_text()
archive = Path('/mnt/e/edk2-samurai-out/kernel81/wifi-firmware-stock.tar')
manifest = json.loads((W / 'reference/kernel81/wifi-firmware-manifest.json').read_text())
assert sha(archive) == manifest['archive_sha256']
with tarfile.open(archive) as t:
    members = {Path(m.name).name: m for m in t.getmembers() if m.isfile()}
    assert set(members) == {f['name'] for f in manifest['files']}
    for f in manifest['files']:
        data = t.extractfile(members[f['name']]).read()
        assert len(data) == f['bytes'] and hashlib.sha256(data).hexdigest() == f['sha256']
report = {'audit': 'PASS', 'scope': 'offline Kconfig resolution and private firmware integrity',
          'candidate_config_sha256': sha(candidate), 'fragment_sha256': sha(W / 'reference/kernel87/wifi-prerequisites.config'),
          'Kconfig_observed_exit_code': result.returncode, 'changed_symbols': changed,
          'preserved': before, 'firmware_archive_sha256': sha(archive),
          'firmware_files_verified': len(members), 'firmware_installed': False,
          'image_built_from_wifi_profile': False, 'profile_deployed': False,
          'wifi_DT_enabled': False, 'mpss_DT_enabled': False,
          'firmware_loading_chain_verified_on_handset': False,
          'actual_QMI_chip_board_ID_known': False,
          'next': 'build isolated dependency image; explicit WLFW/PD/TFTP and board selection; no charging writes'}
(O / 'wifi-profile-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS: diagnostic profile resolved; existing config/Image/DT/CPIO preserved; 35 firmware files verified.')
print('Changed symbols:', len(changed))
