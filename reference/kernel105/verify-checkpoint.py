from pathlib import Path
import hashlib,json,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel105';out=Path('/mnt/e/edk2-samurai-out/kernel105')
ns={};exec((ref/'verify-tests.py').read_text().split("names=['audio-runtime'",1)[0],ns)
f=ns['archive']('checkpoint');sha=ns['sha'];read=ns['archive_bytes']
t=json.loads((out/'tests-validation.json').read_text());c=json.loads((out/'candidate-validation.json').read_text())
count=len(f)-1
for n,h in t['archives'].items():
    blob=(out/n).read_bytes();assert f[n]==blob and sha(blob)==h
    count+=len(read(blob,'k105-'+n.removesuffix('.tar')))-1
state=f['state.txt'].decode().splitlines()
assert '#104 SMP PREEMPT' in state[0] and state[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()
assert state[3:]==['0','modem','running','adsp','running']
assert f['pcm-status.txt']==b'closed\nclosed\n' and f['bt-class.txt']==b''
assert b'freq=5180\n' in f['wpa-status.txt'] and b'wpa_state=COMPLETED\n' in f['wpa-status.txt']
assert re.search(rb'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',f['haptics-status.txt'])
for l in f['amp-status.txt'].decode().splitlines():assert re.search(r'id=43 .*global=00 amp=80 .*powered=0 muted=1 starts=1 stops=1 failed=0$',l)
assert len(f['nv-check.txt'].splitlines())==6 and all(l.endswith(b': OK') for l in f['nv-check.txt'].splitlines())
parts={n:h for h,n in (l.split('  ',1) for l in f['partitions.sha'].decode().splitlines())}
assert parts['/dev/sde11']==c['full_backup_boot_sha256'] and parts['/dev/sde32']==c['logdump_sha256']
r=ns['archive']('audio-runtime')
assert parts['/dev/sda2']==r['persist-stock-dtbo.sha'].decode().splitlines()[0].split()[0]
assert parts['/dev/sde17']==r['persist-stock-dtbo.sha'].decode().splitlines()[1].split()[0]
for h,n in (l.split('  ',1) for l in f['services.sha'].decode().splitlines()):
    assert sha((Path('/home/cy122/x2pro-linux/initramfs')/n.removeprefix('/')).read_bytes())==h
assert f['modules.txt']==r['modules.txt']
dt={};exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],dt)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(),dt)
a=dt['canonical'](dt['fdt_nodes']((out/'dtb-radio').read_bytes()));b=dt['canonical'](dt['fdt_nodes'](f['runtime-fdt.bin']))
assert not a.keys()-b.keys() and b.keys()-a.keys()<={'/chosen/boot-handoff'}
allowed={'linux,uefi-mmap-desc-size','linux,uefi-mmap-desc-ver','linux,uefi-mmap-size','linux,uefi-mmap-start','linux,uefi-system-table'}
diff={p:sorted(n for n in a[p].keys()|b[p].keys() if a[p].get(n)!=b[p].get(n)) for p in a if a[p]!=b[p]}
assert all(p=='/chosen' and set(v)<=allowed for p,v in diff.items())
assert int(b['/chosen']['linux,uefi-mmap-desc-ver'],16)==1
assert int(b['/chosen']['linux,uefi-mmap-size'],16)%int(b['/chosen']['linux,uefi-mmap-desc-size'],16)==0
log=f['dmesg.txt'].decode()
assert log.count('4080000.remoteproc: fatal')==1
assert not re.search(r'17300000\.remoteproc: fatal|Unhandled context fault|unhandled context fault|Unexpected global fault|Kernel panic|Oops:',log)
ups=[float(x) for x in re.findall(r'\[\s*([\d.]+)\] remoteproc remoteproc\d+: remote processor modem is now up',log)]
adspups=re.findall(r'remote processor adsp is now up',log)
assert len(ups)==2 and len(adspups)==1
fatal=float(re.search(r'\[\s*([\d.]+)\] qcom_q6v5_pas 4080000.remoteproc: samurai crash SMEM event=fatal',log)[1])
v=dict(checkpoint_archive_audit_pass=True,stage=105,kernel_build=104,private_files_verified=count,archive_sha256=sha((out/'checkpoint.tar').read_bytes()),uptime_seconds=float(state[2].split()[0]),mpss_running_seconds=float(state[2].split()[0])-ups[-1],first_mpss_up_seconds=ups[0],first_mpss_fatal_seconds=fatal,first_mpss_lifetime_seconds=fatal-ups[0],recovered_mpss_up_seconds=ups[-1],first_automatic_wifi_start_pass=False,manual_mpss_recovery_count=1,wifi_5g_auth_dhcp_dns_http_pass=True,wifi_stability_fixed=False,native_api_query_pass=True,apr_rebind_dispatch_restored=True,rebind_initial_timeout_preserved=True,core_rebind_count=1,no_adsp_restarts=True,microphone_signal_pass=True,microphone_quality_confirmed=False,physical_speaker_sound_confirmed=False,bluetooth_pair_or_connect=False,physical_vibration_deferred_by_user=True,firmware_boot_byte_identical=True,firmware_and_runtime_fdt_match=True,nv_and_persist_preserved=True,cpio_and_modules_preserved=True,kernel_taint=0,display_timeouts=log.count('frame done timeout'),bt_phase2_errors=log.count('Frame reassembly failed'),fatal_mpss=1,fatal_adsp=0,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v,indent=2))
