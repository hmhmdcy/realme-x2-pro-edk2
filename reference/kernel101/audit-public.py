from pathlib import Path
import json, re, subprocess, tarfile
root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel101')
paths=[p for p in (root/'reference/kernel101').rglob('*') if p.is_file()]
paths += [root/name for name in ('README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md',
  'NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md',
  'reference/kernel100/next-session.md','sessions/101-adsp-native-apr-reply-and-radio-regression.md')]
profile=(out.parent/'kernel95/wpa-test-private.conf').read_text()
secrets=[v.strip('"') for v in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$',profile,re.M)]
secrets.append(json.loads((out/'fastboot-identity.json').read_text())['serial'])
with tarfile.open(out/'checkpoint-retry1.tar') as tar:
    for m in tar:
        if m.isfile() and m.name.endswith('-mac-le.bin'):
            b=tar.extractfile(m).read()
            for data in (b,b[::-1]):
                for separator in (':','-'):secrets.append(separator.join(f'{n:02x}' for n in data))
py=sh=links=0
for p in paths:
    b=p.read_bytes()
    assert not b.startswith((b'\x7fELF',b'ANDROID!',bytes.fromhex('d00dfeed'))),p.name
    text=b.decode()
    assert all(s.casefold() not in text.casefold() for s in secrets if s),p.name
    assert not re.search(r'(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',text),p.name
    assert not re.search(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',text),p.name
    assert p.suffix not in ('.img','.bin','.mdt','.mbn','.ko','.exe','.pyc','.xml','.jsn'),p.name
    if p.suffix=='.py':compile(text,str(p),'exec');py+=1
    if p.suffix=='.sh' or p.name in ('samurai-wifi','samurai-radio-address','samurai-modem-remoteproc'):
        subprocess.run(['bash' if 'bin/bash' in text.splitlines()[0] else 'sh','-n',str(p)],check=True);sh+=1
    if p.suffix=='.md':
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
            if '://' in link or link.startswith('#'):continue
            assert (p.parent/link.split('#')[0]).exists(),(p.name,link)
            links+=1
before=json.loads((out/'public-docs-before.json').read_text())
paragraph=lambda t:next(s for s in t.split('\n\n') if s.startswith('2026-10-11 rootfs 进展：'))
assert paragraph((root/'linux-port/README.md').read_text())==paragraph(before['linux-port/README.md'])
hardware=(root/'linux-port/docs/HARDWARE-STATUS.md').read_text().split('| 功能组 |')[1].split('\n已有基础能力：')[0]
rows=re.findall(r'^\| ([^|]+) \|',hardware,re.M)
assert len(rows)==15 and len(set(rows))==15
handoff=(root/'reference/kernel101/next-session.md').read_text().replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/')
assert (root/'NEXT-SESSION.md').read_text()==handoff
check=json.loads((out/'checkpoint-validation.json').read_text())
assert check['verified_private_files']==113 and not check['automatic_wifi_start_pass']
assert check['physical_vibration_deferred_by_user'] and not check['physical_vibration_confirmed']
assert check['adsp_native_version_reply_pass'] and check['alsa_cards_empty'] and not check['alsa_output_tested']
assert check['checkpoint_sha256'] in (root/'sessions/101-adsp-native-apr-reply-and-radio-regression.md').read_text()
ps=json.loads((out/'powershell-validation.json').read_text(encoding='utf-8-sig'))
assert ps['powershell_syntax_pass'] and ps['files']==5
report=dict(public_audit_pass=True,public_files=len(paths),python_syntax_checked=py,shell_syntax_checked=sh,
  powershell_ast_checked=ps['files'],local_markdown_links_checked=links,
  private_credentials_serial_mac_key_and_binary_scan_pass=True,rootfs_paragraph_preserved=True,hardware_groups=15,
  handoff_copy_matches=True,physical_confirmation_deferred=True,no_vibration_question_pending=True,
  automatic_wifi_failure_and_new_two_ghz_drop_recorded=True,adsp_reply_and_empty_sound_card_boundary_recorded=True,goal_complete=False)
(out/'public-docs-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
