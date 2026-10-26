#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import re
import subprocess

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel108'
out = Path('/mnt/e/edk2-samurai-out/kernel108')
names = ['README.md', 'FLYWHEEL.md', 'linux-port/README.md', 'linux-port/docs/HARDWARE-STATUS.md',
         'NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'HANDOVER-NEXT.md', 'DOCS-INDEX.md',
         'sessions/108-display-flicker-and-panel-state-handover.md']
paths = [p for p in ref.iterdir() if p.is_file() and p.name != 'SHA256SUMS'] + [root / name for name in names]
secrets = []
for path in out.parent.glob('kernel*/wpa*private.conf'):
    secrets += [value.strip('"') for value in re.findall(r'^\s*#?\s*(?:ssid|psk)\s*=\s*(.+?)\s*$', path.read_text(), re.M)]
secrets.append(json.loads((out / 'fastboot-identity.json').read_text())['serial'])
for name in ['baseline-boot-private.txt', 'runtime-boot-id-after-private.txt', 'display-expected-boot-private.txt']:
    secrets.append((out / name).read_text(encoding='utf-8-sig').splitlines()[0])
python = shell = links = 0
for path in paths:
    data = path.read_bytes()
    assert not data.startswith((b'\x7fELF', b'ANDROID!', bytes.fromhex('d00dfeed'))), path
    text = data.decode()
    assert all(value.casefold() not in text.casefold() for value in secrets if value), path
    assert not re.search(r'(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', text), path
    assert not re.search(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----', text), path
    assert path.suffix not in ('.tar', '.img', '.bin', '.mbn', '.mdt', '.ko', '.exe', '.wav', '.pyc'), path
    if path.suffix == '.py':
        compile(text, str(path), 'exec')
        python += 1
    if path.suffix == '.sh' or path.name == 'haptics-device':
        subprocess.run(['bash' if 'bin/bash' in text.splitlines()[0] else 'sh', '-n', str(path)], check=True)
        shell += 1
    if path.suffix == '.md':
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
            if '://' in link or link.startswith('#'):
                continue
            assert (path.parent / link.split('#')[0]).exists(), (path, link)
            links += 1
before = json.loads((out / 'public-docs-before.json').read_text())
paragraph = lambda text: next(p for p in text.split('\n\n') if p.startswith('2026-10-11 rootfs 进展：'))
assert paragraph((root / 'linux-port/README.md').read_text()) == paragraph(before['linux-port/README.md'])
hardware = (root / 'linux-port/docs/HARDWARE-STATUS.md').read_text().split('| 功能组 |')[1].split('\n已有基础能力：')[0]
rows = re.findall(r'^\| ([^|]+) \|', hardware, re.M)
assert len(rows) == len(set(rows)) == 15
assert len((root / 'NEXT-SESSION-PROMPT.md').read_text()) < 650
check = json.loads((ref / 'checkpoint-validation.json').read_text())
assert check['checkpoint_archive_audit_pass'] and not check['wifi_data_test_pass']
assert not check['display_cycle_optical_pass'] and not check['permanent_display_fix']
assert not check['new_kernel_built'] and not check['partitions_flashed']
ps = json.loads((out / 'powershell-validation.json').read_text(encoding='utf-8-sig'))
assert ps['powershell_syntax_pass']
assert not re.search(r'^6-5\s+05c6:9505\s+.*Attached', (out / 'usbipd-final-private.txt').read_text(encoding='utf-8-sig'), re.M)
assert (out / 'usbipd-status.txt').read_text(encoding='utf-8-sig').strip() == 'Running'
assert check['checkpoint_sha256'] in (root / names[-1]).read_text()
report = dict(public_audit_pass=True, public_files=len(paths), python_syntax_checked=python,
              shell_syntax_checked=shell, powershell_ast_checked=ps['files'],
              local_markdown_links_checked=links, credentials_identity_binary_scan_pass=True,
              hardware_groups=15, rootfs_paragraph_preserved=True, short_prompt_chars=len((root / 'NEXT-SESSION-PROMPT.md').read_text()),
              failed_display_and_network_tests_retained=True, eud_detached=True, usbipd_running=True,
              no_new_kernel_or_flash=True, goal_complete=False)
(ref / 'public-docs-validation.json').write_text(json.dumps(report, indent=2)+'\n')
entries = [p for p in ref.iterdir() if p.is_file() and p.name != 'SHA256SUMS']
(ref / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(entries)))
print(json.dumps(report, indent=2))
