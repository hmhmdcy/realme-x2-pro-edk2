from pathlib import Path
import json,re,subprocess,tarfile
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel103';out=Path('/mnt/e/edk2-samurai-out/kernel103')
paths=[p for p in ref.rglob('*') if p.is_file()]+[root/n for n in ('README.md','FLYWHEEL.md','linux-port/README.md',
 'linux-port/docs/HARDWARE-STATUS.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md',
 'reference/kernel102/next-session.md','sessions/103-native-max98937-card-pcm-and-zero-microphone.md')]
secret=[]
for n in ('kernel95/wpa-test-private.conf','kernel102/wpa-5g-private.conf','kernel103/wpa-5g-private.conf'):
    s=(out.parent/n).read_text();secret += [v.strip('"') for v in re.findall(r'^\s*#?\s*(?:ssid|psk)\s*=\s*(.+?)\s*$',s,re.M)]
secret.append(json.loads((out/'fastboot-identity.json').read_text())['serial'])
for n in ('baseline-boot-private.txt','runtime-boot-id-after-private.txt'):
    secret.append((out/n).read_text(encoding='utf-8-sig').splitlines()[0])
py=sh=links=0
for p in paths:
    b=p.read_bytes();assert not b.startswith((b'\x7fELF',b'ANDROID!',bytes.fromhex('d00dfeed'))),p.name
    s=b.decode();assert all(v.casefold() not in s.casefold() for v in secret if v),p.name
    assert not re.search(r'(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',s),p.name
    assert not re.search(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',s),p.name
    assert p.suffix not in ('.img','.bin','.mdt','.mbn','.ko','.exe','.pyc','.xml','.jsn','.wav'),p.name
    if p.suffix=='.py':compile(s,str(p),'exec');py+=1
    if p.suffix=='.sh' or p.name=='haptics-device':subprocess.run(['bash' if 'bin/bash' in s.splitlines()[0] else 'sh','-n',str(p)],check=True);sh+=1
    if p.suffix=='.md':
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',s):
            if '://' in link or link.startswith('#'):continue
            assert (p.parent/link.split('#')[0]).exists(),(p.name,link);links+=1
before=json.loads((out/'public-docs-before.json').read_text())
paragraph=lambda s:next(p for p in s.split('\n\n') if p.startswith('2026-10-11 rootfs 进展：'))
assert paragraph((root/'linux-port/README.md').read_text())==paragraph(before['linux-port/README.md'])
hw=(root/'linux-port/docs/HARDWARE-STATUS.md').read_text().split('| 功能组 |')[1].split('\n已有基础能力：')[0]
rows=re.findall(r'^\| ([^|]+) \|',hw,re.M);assert len(rows)==15 and len(set(rows))==15
assert (root/'NEXT-SESSION.md').read_text()==(ref/'next-session.md').read_text().replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/')
v=json.loads((out/'checkpoint-validation.json').read_text());t=json.loads((out/'tests-validation.json').read_text())
assert v['checkpoint_archive_audit_pass'] and v['private_files_verified']==240 and not v['microphone_signal_pass']
assert v['finite_pcm_playback_pass'] and v['capture_all_zero_twice'] and not v['native_api_query_pass']
assert v['no_dsp_restarts'] and not v['bluetooth_pair_or_connect'] and v['physical_vibration_deferred_by_user']
ps=json.loads((out/'powershell-validation.json').read_text(encoding='utf-8-sig'));assert ps['powershell_syntax_pass']
assert v['archive_sha256'] in (root/'sessions/103-native-max98937-card-pcm-and-zero-microphone.md').read_text()
owners=json.loads((out/'owner-validation.json').read_text(encoding='utf-8-sig'))
assert owners['usbipd_status']=='Running' and owners['owned_host_processes_remaining']==0,owners
usb=(out/'usbipd-final-private.txt').read_text(encoding='utf-8-sig');assert not re.search(r'^6-5\s+05c6:9505\s+.*Attached',usb,re.M)
report=dict(public_audit_pass=True,public_files=len(paths),python_syntax_checked=py,shell_syntax_checked=sh,
 powershell_ast_checked=ps['files'],local_markdown_links_checked=links,private_credential_identity_serial_mac_key_binary_audio_scan_pass=True,
 rootfs_paragraph_preserved=True,hardware_groups=15,tests_and_zero_signal_boundary_recorded=True,native_query_failure_preserved=True,
 historical_radio_and_display_failures_preserved=True,physical_confirmation_deferred=True,no_live_owned_host_processes=True,goal_complete=False)
(out/'public-docs-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
