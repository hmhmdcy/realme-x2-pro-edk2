from pathlib import Path
import hashlib,json,os,re,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k198-camss-trace';out.mkdir(mode=0o700);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k198-baseline/boot-id-private.txt').read_bytes();assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512';assert all(not Path('/sys/module/'+n).exists() for n in ['samurai_front_overlay','imx471','i2c_qcom_cci']);camss=Path('/sys/bus/platform/devices/acb3000.camss');assert (camss/'driver').exists()
for process in Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:
  for p in (process/'fd').iterdir():
   try:target=os.readlink(p)
   except OSError:continue
   assert not target.startswith(('/dev/video','/dev/media','/dev/v4l-subdev'))
 except (FileNotFoundError,PermissionError):pass
tracing=Path('/sys/kernel/tracing');root_state={n:(tracing/n).read_bytes() for n in ['tracing_on','set_event','current_tracer']};instance=tracing/'instances/samurai-camera198';assert not instance.exists();original_control=(camss/'power/control').read_text().strip();assert original_control=='auto';before=subprocess.check_output(['dmesg']);old_graph=subprocess.check_output(['media-ctl','-p']);(out/'dmesg-before-private.txt').write_bytes(before);(out/'graph-before-private.txt').write_bytes(old_graph);configured=[];report=dict(stage=198,observations=[])
def observe(label):
 for n,path in [('clocks','/sys/kernel/debug/clk/clk_summary'),('genpd','/sys/kernel/debug/pm_genpd/pm_genpd_summary'),('interrupts','/proc/interrupts')]:
  if Path(path).exists():(out/(label+'-'+n+'-private.txt')).write_bytes(Path(path).read_bytes())
 report['observations'].append(dict(label=label,camss=(camss/'power/runtime_status').read_text().strip(),monotonic=time.monotonic()));(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
try:
 instance.mkdir();(instance/'tracing_on').write_text('0');(instance/'buffer_size_kb').write_text('128');(instance/'current_tracer').write_text('nop')
 for name in ['regmap/regmap_reg_write','regmap/regmap_reg_read','clk/clk_enable','clk/clk_disable','clk/clk_set_rate']:
  event=instance/'events'/name;predicate='name ~ "*ad00000*"' if name.startswith('regmap/') else 'name ~ "cam_cc_*" || name ~ "gcc_camera_*"';(event/'filter').write_text(predicate);configured.append(event);(event/'enable').write_text('1')
 (instance/'trace').write_text('');(instance/'tracing_on').write_text('1');(instance/'trace_marker').write_text('baseline');observe('baseline')
 (instance/'trace_marker').write_text('camss-force-on');(camss/'power/control').write_text('on');time.sleep(.2);observe('camss-on')
 (instance/'trace_marker').write_text('camss-auto');(camss/'power/control').write_text('auto');time.sleep(.2);observe('camss-auto')
 tool=root/'k197-offline-tools/tpg-control-aarch64-private';assert hashlib.sha256(tool.read_bytes()).hexdigest()=='768705482162ad0056a8a949f4a95f6b922432dd2676ec54beaf0d8433a0c759';(instance/'trace_marker').write_text('tpg-start')
 p=subprocess.run([str(tool),'--capture',str(out/'first-frame-private.raw')],capture_output=True,timeout=35);(out/'capture-private.log').write_bytes(p.stdout+p.stderr);report['capture_returncode']=p.returncode;(instance/'trace_marker').write_text('tpg-end');observe('after-tpg')
finally:
 if (camss/'power/control').read_text().strip()!=original_control:(camss/'power/control').write_text(original_control)
 if instance.exists():
  (instance/'tracing_on').write_text('0');(out/'regmap-clock-trace-private.txt').write_bytes((instance/'trace').read_bytes())
  for event in configured:(event/'enable').write_text('0')
  instance.rmdir()
 report['root_trace_state_preserved']=all((tracing/n).read_bytes()==v for n,v in root_state.items());report['private_trace_instance_removed']=not instance.exists();(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after);new_graph=subprocess.check_output(['media-ctl','-p']);(out/'graph-after-private.txt').write_bytes(new_graph);report.update(topology_restored=new_graph==old_graph,fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()));(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');assert report['root_trace_state_preserved'] and report['topology_restored'] and all(v==0 for v in report['fault_delta'].values()) and report['taint']==512;print(json.dumps(report));print(after[len(before):].decode(errors='replace')[-2500:])
