"""Recheck current modules, camera payloads, app additions and idle cleanup."""
from pathlib import Path
import ast
import json
import host
R=Path(__file__).resolve().parent
s=(R.parent/'kernel239/final-health.py').read_text()
s=s.replace("out = root / 'k239-final-health'", "out = root / 'k240-final-health'")
s=s.replace("assert len(new) == 944 and set(old) == set(new)", """snapshot_transaction=root/'k240-snapshot-app-transaction'
assert json.loads((snapshot_transaction/'transaction-state-private.json').read_text())['state']=='verified'
snapshot_before=records((snapshot_transaction/'installed-before-private.txt').read_bytes())
additions=json.loads((root/'k240-snapshot-host-packages/manifest.json').read_text())['packages']
added={item['name']:item['version'] for item in additions}
assert len(added)==14 and len(snapshot_before)==944 and len(new)==958
assert set(new)==set(old)|set(added) and set(new)-set(snapshot_before)==set(added)
assert all(new[n]==v for n,v in snapshot_before.items())
assert all('V:'+v in new[n].splitlines() for n,v in added.items())
assert set(Path('/etc/apk/world').read_text().splitlines())==set((snapshot_transaction/'world-before-private.txt').read_text().splitlines())|{'snapshot=51.0-r0'}
assert json.loads((root/'k240-snapshot-launcher-transaction/state-private.json').read_text())['state']=='verified'
assert json.loads((root/'k240-snapshot-dbus-activation-r3/summary.json').read_text())['real_user_session_dbus_activation_verified']
user=__import__('pwd').getpwuid(10000)
for rel,item in json.loads((root/'k240-snapshot-launcher-transaction/override-manifest-private.json').read_text()).items():
 path=Path(user.pw_dir)/'.local/share'/rel
 assert sha(path.read_bytes())==item['sha256'] and stat.S_IMODE(path.stat().st_mode)==item['mode'] and path.stat().st_uid==item['uid']
for rel,text in json.loads((root/'k240-snapshot-launcher-audit/original-launch-files-private.json').read_text()).items():
 assert (Path('/usr/share')/rel).read_text()==text
current_contexts=['k240-upright-paired-r15','k240-upright-paired-r15-r2','k240-megapixels-startup','k240-snapshot-cairo','k240-snapshot-cairo-r2','k240-snapshot-mmap','k240-snapshot-mmap-r2']
for name in current_contexts:assert json.loads((root/name/'state-private.json').read_text())['state']=='terminal'
for name in current_contexts[1:]:
 value=json.loads((root/name/'summary.json').read_text())
 assert all(value[k] for k in ['all_formats_restored','media_graph_restored','sensor_controls_restored','rails_unchanged','camera_devices_suspended','mclk1_mclk2_disabled'])
 assert not value['restore_errors'] and not any(value['fault_delta'].values())
assert json.loads((root/'k240-snapshot-fault-stop/summary.json').read_text())['exact_existing_faulting_snapshot_stopped']
observed_faults=json.loads((root/'k240-snapshot-observed-stream/summary.json').read_text())['fault_delta']
assert observed_faults['gpu']==10
cpu_flow=json.loads((root/'k240-snapshot-mmap-r2/frame-flow-analysis.json').read_text())
assert cpu_flow['pipewire_new_buffer_count']==1436 and cpu_flow['gtk_cpu_mmap_download_count']==600
assert not cpu_flow['startup']['application_gpu_device_fds']""")
s=s.replace("assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'", """baseline_log=(root/'k240-snapshot-fault-stop/dmesg-private.txt').read_bytes()
needles=dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received',bt_reassembly=b'Frame reassembly failed')
post_stop_delta={k:log.count(v)-baseline_log.count(v) for k,v in needles.items()}
assert not any(post_stop_delta.values())
assert faults['gpu']>0 and not any(v for k,v in faults.items() if k!='gpu')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'""")
s=s.replace("('k236', 'k238', 'k239')", "('k236', 'k238', 'k239', 'k240')")
s=s.replace('report = dict(stage=239,','report = dict(stage=240,')
s=s.replace('package_count=944,','package_count=958,original944_r15_records_unchanged=True,snapshot_added_packages=14,')
s=s.replace('packages_userspace_loader_exact_except_verified_seven_package_upgrade=True,','packages_userspace_loader_exact_except_prior_seven_package_upgrade_and14_snapshot_additions=True,')
s=s.replace('taint=0, fault_counts=faults,', 'taint=0, fault_counts=faults, historical_default_vulkan_gpu_faults_retained=True, fault_delta_since_faulting_snapshot_stopped=post_stop_delta, all240_camera_workers_terminal=True, snapshot_cpu_mmap_front_preview_verified=True, snapshot_per_user_desktop_and_real_dbus_cpu_flags_verified=True, snapshot_recycle_errors_and_photography_open=True,')
ast.parse(s);(R/'native-final-health.py').write_text(s)
p=host.ssh('python3 -',input=s.encode(),timeout=110)
(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)
data=json.loads(p.stdout);(R/'final-health-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
