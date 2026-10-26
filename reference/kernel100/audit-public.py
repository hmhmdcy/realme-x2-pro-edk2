from pathlib import Path
import hashlib, json, re, subprocess, tarfile

root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel100')
paths=list((root/'reference/kernel99').glob('*'))+list((root/'reference/kernel100').glob('*'))
paths += [root/name for name in ('README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md',
    'NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md',
    'sessions/99-aw8697-haptics-and-ufs-readiness.md','sessions/100-all-source-readiness-and-first-mpss-crash.md')]
paths=[p for p in paths if p.is_file()]
profile=(out.parent/'kernel95/wpa-test-private.conf').read_text()
secrets=[value.strip('"') for value in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$',profile,re.M)]
secrets.append(json.loads((out/'fastboot-identity.json').read_text())['serial'])
with tarfile.open(out/'checkpoint-final-retry1.tar') as handle:
    for member in handle:
        if member.isfile() and member.name.endswith('-mac-le.bin'):
            address=handle.extractfile(member).read()
            for data in (address,address[::-1]):
                for separator in (':','-'):
                    secrets.append(separator.join(f'{b:02x}' for b in data))
checked_python=checked_shell=checked_links=0
for path in paths:
    data=path.read_bytes()
    assert not data.startswith((b'\x7fELF',b'ANDROID!',bytes.fromhex('d00dfeed'))),path.name
    text=data.decode()
    assert all(secret.casefold() not in text.casefold() for secret in secrets if secret),path.name
    assert not re.search(r'(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',text),path.name
    assert not re.search(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',text),path.name
    if path.suffix=='.py':compile(text,str(path),'exec');checked_python+=1
    if path.suffix=='.sh':subprocess.run(['sh' if 'bin/bash' not in text.splitlines()[0] else 'bash','-n',str(path)],check=True);checked_shell+=1
    if path.suffix=='.md':
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
            if '://' in link or link.startswith('#'):continue
            target=path.parent/link.split('#')[0]
            assert target.exists(),(path.name,link)
            checked_links+=1
before=json.loads((out/'public-docs-before.json').read_text())
paragraph=lambda s:next(p for p in s.split('\n\n') if p.startswith('2026-10-11 rootfs 进展：'))
assert paragraph((root/'linux-port/README.md').read_text())==paragraph(before['linux-port/README.md'])
hardware=(root/'linux-port/docs/HARDWARE-STATUS.md').read_text().split('| 功能组 |')[1].split('\n已有基础能力：')[0]
rows=re.findall(r'^\| ([^|]+) \|',hardware,re.M)
assert len(rows)==15 and len(set(rows))==15
handoff=(root/'reference/kernel100/next-session.md').read_text().replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/')
assert (root/'NEXT-SESSION.md').read_text()==handoff
checkpoint=json.loads((out/'checkpoint-validation.json').read_text())
assert checkpoint['verified_private_files']==86 and not checkpoint['automatic_wifi_start_pass'] and not checkpoint['physical_vibration_confirmed']
session=(root/'sessions/100-all-source-readiness-and-first-mpss-crash.md').read_text()
assert checkpoint['checkpoint_sha256'] in session and checkpoint['goal_complete'] is False
report=dict(public_audit_pass=True,public_files=len(paths),python_syntax_checked=checked_python,
    shell_syntax_checked=checked_shell,local_markdown_links_checked=checked_links,
    credential_serial_mac_and_private_key_scan_pass=True,rootfs_paragraph_byte_text_preserved=True,
    hardware_groups=15,handoff_copy_matches=True,physical_confirmation_pending=True,
    automatic_radio_failure_recorded=True,goal_complete=False)
(out/'public-docs-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
