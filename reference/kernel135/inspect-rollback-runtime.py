from pathlib import Path
import tarfile,hashlib,json,subprocess,sys
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel135')
with tarfile.open(out/'rollback-final-private.tar.gz') as tf:
 data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);assert hashlib.sha256(data[n.removeprefix('./')]).hexdigest()==h
assert b'#132 SMP PREEMPT' in data['uname.txt'] and b'7.3.0-rc6-rmx1931-samurai-k132+' in data['uname.txt']
assert data['boot-id-private.txt'].strip()!=(out/'failed-boot-id-private.txt').read_bytes().strip()
(out/'embedded-boot-id-private.txt').write_bytes(data['boot-id-private.txt'])
(out/'embedded-live-fdt-private.dtb').write_bytes(data['live-fdt-private.dtb'])
subprocess.run(['dtc','-I','dtb','-O','dts','-o',str(out/'embedded-live-fdt-private.dts'),str(out/'embedded-live-fdt-private.dtb')],stderr=subprocess.DEVNULL,check=True)
for name in ['dmesg.txt','services.txt','drm-resolved.txt','connector.txt','state.txt','sensors.txt','radio-audio.txt','pcm.txt','camera-nodes.txt']:
 (out/name.replace('.txt','-embedded-runtime-private.txt')).write_bytes(data[name])
parts={n:h for h,n in (l.split('  ',1) for l in data['partition-check.sha256'].decode().splitlines())}
boot=json.loads((r/'reference/kernel132/boot-package-validation.json').read_text())
assert parts['/dev/sde11']==boot['boot_sha256'] and parts['/dev/sde32']==boot['logdump_sha256']
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
with tarfile.open(out.parent/'kernel112/layout-after.tar') as tf: old={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for dev in ['sda','sdb','sdc','sdd','sde','sdf']:
 for suffix in ['geometry','head','tail']:assert data[dev+'.'+suffix]==old[dev+'.'+suffix]
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
with tarfile.open(out.parent/'kernel132/modules-k132-private.tar.gz') as archive:
 module=next(m for m in archive if m.name.endswith('/kernel/drivers/net/ipa/ipa.ko'))
 assert data['ipa-module.sha256'].split()[0].decode()==hashlib.sha256(archive.extractfile(module).read()).hexdigest()
sys.path.insert(0,str(r/'reference/kernel113'))
from inspect_live_fdt import fdt
expected=fdt((out.parent/'kernel132/DTB-k132-private').read_bytes());live=fdt(data['live-fdt-private.dtb'])
assert expected.keys()==live.keys()
for name,props in expected.items():assert all(live[name].get(k)==v for k,v in props.items()),name
assert live['/soc@0/camss@acb3000']['status']==b'okay\0'
assert data['console-node.txt']==b'character special file 600 5 1 0 0\n'
assert b'unable to open an initial console' not in data['dmesg.txt']
assert b'Run /init as init process' in data['dmesg.txt']
node='/soc@0/geniqup@8c0000/i2c@884000/charger@5c'
assert live[node]['compatible']==b'mps,mp2650\0' and live[node]['reg']==(0x5c).to_bytes(4,'big')
assert b'POWER_SUPPLY_ONLINE=1\n' in data['mp2650-uevent.txt'] and b'POWER_SUPPLY_STATUS=' in data['mp2650-uevent.txt']
assert len(data['mp2650-modes.txt'].splitlines())==4 and all(l.startswith(b'444 ') for l in data['mp2650-modes.txt'].splitlines())
assert data['full-module-check.txt'].count(b': OK')>=770 and b'FAILED' not in data['full-module-check.txt']
assert b'started' in data['bluez-service.txt']
assert data['state.txt'].splitlines()[-1]==b'0' and data['phosh.txt'].strip() and data['phoc.txt'].strip()
assert data['gui-config-check.txt'].count(b': OK')==3
assert data['connector.txt'].strip()==b'connected'
assert b'freq: 5180' in data['wifi-link-private.txt']
assert b'at wcd934x_comp_probe' not in data['dmesg.txt']
assert b'at clk_core_disable' not in data['dmesg.txt']
assert b'at clk_core_unprepare' not in data['dmesg.txt']
assert b'ASoC error (-28)' not in data['dmesg.txt']
report=dict(stage=135,rollback_target=132,failed_candidate135_rejected=True,automatic_desktop_processes_recovered_without_panel_reprobe_or_greetd_marker_change=True,active_crtc_count=data['drm-state.txt'].count(b'active=1'),inactive_crtc_count=data['drm-state.txt'].count(b'active=0'),continuous_display_acceptance=False,full_automatic_display_acceptance=False,dpu_timeout_events=data['dmesg.txt'].count(b'frame done timeout'),gpu_fault_events=data['dmesg.txt'].count(b'*** gpu fault'),permanent_display_fix=False,usb_input134_driver_currently_absent_after_rollback=True,original_gui_configuration_unchanged=True,codec_enospc_and_probe_warn_absent_this_boot=True,dsi_clock_warns_absent_this_boot=True,persistent_mp2650_standard_power_supply_auto_registered=True,charger_attributes_read_only=True,all_matching_modules_verified=True,bluez_service_started=True,initial_console_warning_count=0,live_console_char_5_1_root0600=True,original_init_userspace_reached=True,embedded132_dtb_with_charger_verified=True,all_live_dtb_expected_nodes_and_properties_match=True,kernel_build=132,new_boot_verified=True,flash_logdump_bytes_match=True,boot_bytes_match_embedded132=True,persist_unchanged=True,gpt18_unchanged=True,nv6_source4_vendor1_unchanged=True,matching_fixed_ipa_module=True,taint=int(data['state.txt'].splitlines()[-1]),phosh_running=bool(data['phosh.txt'].strip()),phoc_running=bool(data['phoc.txt'].strip()),display_connected=data['connector.txt'].strip()==b'connected',drm_resolved=data['drm-resolved.txt'].decode().strip(),hardware_complete=False,camss_runtime_pending=True,goal_complete=False)
(r/'reference/kernel135/rollback-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
