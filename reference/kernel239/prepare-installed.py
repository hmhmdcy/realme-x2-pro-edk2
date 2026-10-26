from pathlib import Path
import ast,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239');ROOT=R.parents[1]
assert json.loads((R/'r15-package-install-validation.json').read_text())['transaction_state']=='verified'
source=(R/'native-r15-startup.py').read_text().replace('k239-r15-startup','k239-r15-installed-startup')
old="assert json.loads((root/'k239-candidate-stage/summary.json').read_text())['ram_candidate_staged']";assert source.count(old)==1
source=source.replace(old,"assert json.loads((root/'k239-r15-package-transaction/install-summary.json').read_text())['transaction_state']=='verified'")
start=source.index(" prefix=Path('/run/samurai-camera239-r15')");end=source.index('\n dims=',start)
source=source[:start]+" env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG,Debayer:DEBUG,IPASoftBL:DEBUG')"+source[end:]
source=source.replace("if '/run/samurai-camera239-r15/' in line", "if '/usr/lib/libcamera' in line").replace("'/run/samurai-camera239-r15/usr/lib/'+name", "'/usr/lib/'+name")
source=source.replace('same_camera_two_start_stop_runs=True,','default_environment_without_candidate_overrides=True,same_camera_two_start_stop_runs=True,')
ast.parse(source);(R/'native-installed-startup.py').write_text(source)
for old,new in [('start-r15-startup.py','start-installed-startup.py'),('poll-r15-startup.py','poll-installed-startup.py'),('analyze-r15-startup.py','analyze-installed-startup.py')]:
 text=(R/old).read_text().replace('native-r15-startup.py','native-installed-startup.py').replace('k239-r15-startup','k239-r15-installed-startup').replace('r15-startup-launch','r15-installed-startup-launch').replace('r15-startup-poll','r15-installed-startup-poll').replace('r15-startup-validation.json','r15-installed-startup-validation.json').replace('r15-startup-parameter-log-lines-private.json','r15-installed-startup-parameter-log-lines-private.json').replace('r15-startup-analysis.json','r15-installed-startup-analysis.json')
 ast.parse(text);(R/new).write_text(text)
# Reuse the already exercised idle policy reload, with current identity and
# observations that explicitly guard Bluetooth transports/connections.
tree=ast.parse((R.parent/'kernel225/reload-wireplumber.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets));code=ast.literal_eval(node.value)
code=code.replace('/var/lib/samurai/k225-baseline','/var/lib/samurai/k236-runtime').replace('k225-r13-package-transaction','k239-r15-package-transaction').replace('k225-r13-package-candidates','k239-r15-package-candidates').replace('stage=225','stage=239').replace('new_r13_camera_libraries_loaded','new_r15_camera_libraries_loaded')
anchor="before=subprocess.check_output(['dmesg']);";assert code.count(anchor)==1
code=code.replace(anchor,"""import dbus
bus=dbus.SystemBus(private=True)
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager')
before_bluez=objects.GetManagedObjects()
before_connections={str(k):bool(v['org.bluez.Device1'].get('Connected',False)) for k,v in before_bluez.items() if 'org.bluez.Device1' in v}
assert all(str(v['org.bluez.MediaTransport1'].get('State','idle'))=='idle' for v in before_bluez.values() if 'org.bluez.MediaTransport1' in v),'Active Bluetooth media transport; preserve policy process'
"""+anchor)
anchor="state.update(state='verified',new_pid=int(new.name));";assert code.count(anchor)==1
code=code.replace(anchor,"""after_bluez=objects.GetManagedObjects()
after_connections={str(k):bool(v['org.bluez.Device1'].get('Connected',False)) for k,v in after_bluez.items() if 'org.bluez.Device1' in v}
assert {k:v for k,v in before_connections.items() if v}=={k:v for k,v in after_connections.items() if v},'Bluetooth connection state changed; do not issue reconnect commands'
bus.close()
"""+anchor)
code=code.replace('reboot_not_used=True)', 'reboot_not_used=True,bluetooth_media_was_idle=True,bluetooth_connected_devices_unchanged=True,no_pair_connect_or_disconnect_requested=True)')
ast.parse(code)
text="from pathlib import Path\nimport json\nimport host\nR=Path(__file__).resolve().parent\ncode="+repr(code)+"\nresult=host.ssh('python3 -',input=code.encode(),timeout=55)\n(host.PRIVATE/'policy-reload-host-private.log').write_bytes(result.stdout+result.stderr)\nreport=json.loads(result.stdout)\n(R/'wireplumber-reload-validation.json').write_text(json.dumps(report,indent=2)+'\\n')\nprint(json.dumps(report))\n"
ast.parse(text);(R/'reload-wireplumber.py').write_text(text)
p=P/'current-work-private.json';state=json.loads(p.read_text());state.update(state='r15/r10 installed and native payload/rollback verified; default capture/policy reload pending',installed_libcamera='r15',installed_config='r10',r15_default_installed=True,active_build_session=None,next='Verify default startup with no candidate environment, reload idle policy preserving desktop and BlueZ connected state, then final health/evidence.');p.write_text(json.dumps(state,indent=2)+'\n')
checkpoint=(ROOT/'NEXT-SESSION.md').read_text().replace('当前默认r13/r8，RAM','当前默认已升级r15/r10（七包/49文件/944包总数，默认取流和策略重载待验），RAM')
(ROOT/'NEXT-SESSION.md').write_text(checkpoint)
print('Prepared default-environment two-start test and guarded idle policy reload; installed r15 recorded')
