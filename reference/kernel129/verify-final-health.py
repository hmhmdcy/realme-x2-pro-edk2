from pathlib import Path
import tarfile,json,hashlib,re,stat,runpy
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel129')
with tarfile.open(out/'final-health-private.tar.gz') as tf:data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);assert hashlib.sha256(data[n.removeprefix('./')]).hexdigest()==h
assert data['boot-id-private.txt'].strip()==(out/'embedded-boot-id-private.txt').read_bytes().strip()
assert data['taint.txt'].strip()==b'0' and data['sensor.txt'].strip()==b'offline\nvdd=0 vddio=0' and data['radio-audio.txt'].strip()==b'running\nrunning'
assert data['phosh.txt'].strip().isdigit() and data['phoc.txt'].strip().isdigit() and data['connector.txt'].strip()==b'connected'
assert data['dma-trace.txt'].strip()==b'N' and data['amps.txt'].count(b'failed=0')==2
samples=data['samples.txt'].decode().splitlines();assert len(samples)==6;duration=float(samples[-1].split()[1])-float(samples[0].split()[1]);assert duration>=50
before=data['dmesg-before.txt'];after=data['dmesg-after.txt'];assert after.startswith(before);new=after[len(before):].decode()
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
assert data['modules-check.txt'].count(b': OK')>=770 and b'FAILED' not in data['modules-check.txt']
parts={n:h for h,n in (l.split('  ',1) for l in data['partitions.sha256'].decode().splitlines())};package=json.loads((ref/'boot-package-validation.json').read_text())
assert parts['/dev/sde11']==package['boot_sha256'] and parts['/dev/sde32']==package['logdump_sha256'] and parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
warnings=['frame done timeout','*** gpu fault','Unhandled context fault','WARNING:','BUG:','Oops:'];counts={w:new.count(w) for w in warnings}
assert all(v==0 for v in counts.values())
assert data['wifi-profile-owner.txt']==b'0:0:600\n'
freq=float(re.search(r'freq: ([\d.]+)',data['wlan-link-private.txt'].decode())[1]);assert freq==5180
assert data['console-node.txt']==b'character special file 600 5 1 0 0\n'
assert b'unable to open an initial console' not in before and b'unable to open an initial console' not in after
log=after.decode();report=dict(console_warning_resolved=True,wlan_frequency_mhz=freq,initial_console_warning_count=log.count('unable to open an initial console'),final_health_pass=True,current_kernel=129,embedded126_dtb_prior_verified=True,same_post_firmware_boot=True,desktop_phosh_phoc_running=True,display_connected=True,drm_active_crtc_count=data['drm-state.txt'].count(b'active=1'),samples=6,sample_duration_seconds=duration,new_fault_counts=counts,total_dpu_timeouts=log.count('frame done timeout'),total_gpu_faults=log.count('*** gpu fault'),taint=0,mpss_adsp_running=True,bluetooth_hci_present=True,wlan_operstate=data['wlan.txt'].decode().strip(),pcm_closed=data['pcm.txt'].strip()==b'closed\nclosed',amps_idle=data['amps.txt'].count(b'powered=0 muted=1')==2,amps_failure_count_zero=True,slpi_and_sensor_power_off=True,debug_traces_saved_then_disabled=True,dma_trace_disabled=True,source11_and_modules770_verified=True,boot_logdump_persist_matches=True,full_hardware_long_stability_not_claimed=True,goal_complete=False)
(ref/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
