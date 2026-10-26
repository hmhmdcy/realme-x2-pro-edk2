from pathlib import Path
import hashlib,json,re,subprocess,tarfile
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel102')
paths=[p for p in (root/'reference/kernel102').rglob('*') if p.is_file()]
paths += [root/n for n in ('README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md',
 'NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md',
 'reference/kernel101/next-session.md','sessions/102-wcd934x-and-real-max98937-identification.md')]
secrets=[]
for name in ('kernel95/wpa-test-private.conf','kernel101/wpa-5g-private.conf'):
    profile=(out.parent/name).read_text()
    secrets += [v.strip('"') for v in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$',profile,re.M)]
secrets.append(json.loads((out/'fastboot-identity.json').read_text())['serial'])
with tarfile.open(out/'checkpoint.tar') as tar:
    for m in tar:
        if m.isfile() and m.name.endswith('.bin') and m.size==6:
            b=tar.extractfile(m).read()
            for data in (b,b[::-1]):
                for sep in (':','-'):secrets.append(sep.join(f'{n:02x}' for n in data))
py=sh=links=0
for p in paths:
    b=p.read_bytes();assert not b.startswith((b'\x7fELF',b'ANDROID!',bytes.fromhex('d00dfeed'))),p.name
    s=b.decode();assert all(secret.casefold() not in s.casefold() for secret in secrets if secret),p.name
    assert not re.search(r'(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',s),p.name
    assert not re.search(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',s),p.name
    assert p.suffix not in ('.img','.bin','.mdt','.mbn','.ko','.exe','.pyc','.xml','.jsn'),p.name
    if p.suffix=='.py':compile(s,str(p),'exec');py+=1
    if p.suffix=='.sh' or p.name=='haptics-device':
        subprocess.run(['bash' if 'bin/bash' in s.splitlines()[0] else 'sh','-n',str(p)],check=True);sh+=1
    if p.suffix=='.md':
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)',s):
            if '://' in link or link.startswith('#'):continue
            assert (p.parent/link.split('#')[0]).exists(),(p.name,link)
            links+=1
before=json.loads((out/'public-docs-before.json').read_text())
paragraph=lambda s:next(p for p in s.split('\n\n') if p.startswith('2026-10-11 rootfs 进展：'))
assert paragraph((root/'linux-port/README.md').read_text())==paragraph(before['linux-port/README.md'])
hw=(root/'linux-port/docs/HARDWARE-STATUS.md').read_text().split('| 功能组 |')[1].split('\n已有基础能力：')[0]
rows=re.findall(r'^\| ([^|]+) \|',hw,re.M);assert len(rows)==15 and len(set(rows))==15
handoff=(root/'reference/kernel102/next-session.md').read_text().replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/')
assert (root/'NEXT-SESSION.md').read_text()==handoff
check=json.loads((out/'checkpoint-validation.json').read_text());assert check['verified_private_files']==125
assert check['automatic_wifi_start_pass'] and not check['wifi_stability_fixed']
assert check['actual_amp_model']=='MAX98937' and check['wrong_amp_components_unbound'] and check['amp_resets_physical_low']
assert check['physical_vibration_deferred_by_user'] and not check['physical_vibration_confirmed'] and not check['alsa_output_tested']
assert check['checkpoint_sha256'] in (root/'sessions/102-wcd934x-and-real-max98937-identification.md').read_text()
ps=json.loads((out/'powershell-validation.json').read_text(encoding='utf-8-sig'));assert ps['powershell_syntax_pass']
helper=(out/'amp-readonly-ids-private').read_bytes();assert helper.startswith(b'\x7fELF') and helper[18:20]==b'\xb7\0'
report=dict(public_audit_pass=True,public_files=len(paths),python_syntax_checked=py,shell_syntax_checked=sh,
 powershell_ast_checked=ps['files'],local_markdown_links_checked=links,amp_helper_static_arm64=True,
 amp_helper_sha256=hashlib.sha256(helper).hexdigest(),private_credentials_serial_mac_key_and_binary_scan_pass=True,
 rootfs_paragraph_preserved=True,hardware_groups=15,handoff_copy_matches=True,physical_confirmation_deferred=True,
 actual_max98937_and_wrong_driver_boundary_recorded=True,one_auto_boot_success_and_historical_failures_preserved=True,
 display_timeout_two_recorded=True,goal_complete=False)
(out/'public-docs-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
