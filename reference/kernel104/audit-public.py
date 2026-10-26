from pathlib import Path
import json, re, subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel104';out=Path('/mnt/e/edk2-samurai-out/kernel104')
names=['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md','reference/kernel103/next-session.md','sessions/104-native-digital-microphones-and-first-boot-radio-failure.md']
paths=[p for p in ref.rglob('*') if p.is_file()]+[root/n for n in names]
secrets=[]
for n in ('kernel95/wpa-test-private.conf','kernel103/wpa-5g-private.conf','kernel104/wpa-5g-private.conf'):
    secrets += [v.strip('"') for v in re.findall(r'^\s*#?\s*(?:ssid|psk)\s*=\s*(.+?)\s*$',(out.parent/n).read_text(),re.M)]
secrets.append(json.loads((out/'fastboot-identity.json').read_text())['serial'])
for n in ('baseline-boot-private.txt','runtime-boot-id-after-private.txt'):
    secrets.append((out/n).read_text().splitlines()[0])
python=shell=links=0
for p in paths:
    b=p.read_bytes();assert not b.startswith((b'\x7fELF',b'ANDROID!',bytes.fromhex('d00dfeed'))),p.name
    s=b.decode();assert all(v.casefold() not in s.casefold() for v in secrets if v),p.name
    assert not re.search(r'(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',s),p.name
    assert not re.search(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',s),p.name
    assert p.suffix not in ('.img','.bin','.mdt','.mbn','.ko','.exe','.pyc','.xml','.jsn','.wav'),p.name
    if p.suffix=='.py':compile(s,str(p),'exec');python+=1
    if p.suffix=='.sh' or p.name=='haptics-device':subprocess.run(['bash' if 'bin/bash' in s.splitlines()[0] else 'sh','-n',str(p)],check=True);shell+=1
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
assert v['checkpoint_archive_audit_pass'] and v['private_files_verified']==174
assert all(m['signal_path_pass'] and m['steady_clipped_samples']==0 and m['steady_distinct']>32 and m['power_off_after_close'] for m in t['microphones'])
assert v['microphone_signal_pass'] and not v['microphone_quality_confirmed'] and not v['physical_speaker_sound_confirmed']
assert v['fatal_mpss']==1 and v['manual_mpss_recovery_count']==1 and not v['first_automatic_wifi_start_pass']
assert not v['native_api_query_pass'] and v['core_rebind_count']==1 and v['no_adsp_restarts']
assert not v['bluetooth_pair_or_connect'] and v['physical_vibration_deferred_by_user']
ps=json.loads((out/'powershell-validation.json').read_text(encoding='utf-8-sig'));assert ps['powershell_syntax_pass']
assert v['archive_sha256'] in (root/names[-1]).read_text()
owners=json.loads((out/'owner-validation.json').read_text(encoding='utf-8-sig'))
assert owners['usbipd_status']=='Running' and owners['owned_host_processes_remaining']==0
usb=(out/'usbipd-final-private.txt').read_text(encoding='utf-8-sig');assert not re.search(r'^6-5\s+05c6:9505\s+.*Attached',usb,re.M)
report=dict(public_audit_pass=True,public_files=len(paths),python_syntax_checked=python,shell_syntax_checked=shell,powershell_ast_checked=ps['files'],
 local_markdown_links_checked=links,credentials_serial_boot_id_mac_key_audio_binary_scan_pass=True,hardware_groups=15,rootfs_paragraph_preserved=True,
 three_dmic_steady_nonzero_capture_proved=True,physical_audio_quality_unconfirmed=True,first_automatic_radio_failure_and_single_recovery_preserved=True,
 native_api_reply_unknown_status_and_invalid_rebind_boundary_recorded=True,no_live_owned_host_helpers=True,goal_complete=False)
(out/'public-docs-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
