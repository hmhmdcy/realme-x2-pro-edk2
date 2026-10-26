"""One normal IMX471 OF probe and runtime-PM observation, then restore."""
from pathlib import Path
import hashlib,json,mmap,os,re,shutil,subprocess,threading,time
common=Path('/var/lib/samurai/k195-modules/probe-q-reset-address.py').read_text().split('report=dict(',1)[0]
common=common.replace("out=root/'k195-q-reset'","out=root/'k200-front-capture-r2'").replace('k195-baseline','k200-camera-baseline').replace("assert not Path('/sys/module/samurai_cci_bringup').exists()","assert Path('/sys/module/samurai_cci_bringup').exists()")
common=common.replace("read_text().strip()=='512'","read_text().strip()=='0'");exec(compile(common,'<verified-i2c-prefix>','exec'));stage=root/'k200-modules';before=json.loads((root/'k200-front-session/before-private.json').read_text());live=json.loads((root/'k200-live-prepare-r3/live-input.json').read_text());overlay=json.loads((stage/'overlay-build-validation.json').read_text());manifest=json.loads((stage/'manifest.json').read_text())
assert not Path('/sys/module/samurai_camera_perf').exists()
assert snapshot(4)==before['pmic'] and sample(0)==0 and sample(3)==1 and Path('/sys/module/samurai_vio_phandle').exists()
for r in manifest:assert hashlib.sha256((stage/r['file']).read_bytes()).hexdigest()==r['sha256']
assert int(Path('/sys/module/samurai_vio_phandle/parameters/assigned_handle').read_text())==live['vio_phandle']==overlay['fresh_runtime_handles']['VIO_PHANDLE']
fw=Path('/lib/firmware/samurai/k196-front.dtbo');assert not fw.exists();fw.parent.mkdir(exist_ok=True);assert hashlib.sha256((stage/'front.dtbo').read_bytes()).hexdigest()==overlay['dtbo_sha256'];shutil.copyfile(stage/'front.dtbo',fw)
report=dict(stage=200,attempts=[],before=before,pm_observations=[],register_restores=[]);before_log=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before_log);traced=False;old_filter=None;tracefs=Path('/sys/kernel/tracing');sensor=Path('/sys/bus/i2c/devices/7-0010');camss=Path('/sys/bus/platform/devices/acb3000.camss');camdriver=Path('/sys/bus/platform/drivers/qcom-camss');camss_refreshed=False;camss_candidate_loaded=False;camss_original_removed=False;original_camss=None
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def command(args):
 p=subprocess.run(args,capture_output=True,timeout=30);report['attempts'].append(dict(action=args[0],module=args[-1].split('/')[-1],returncode=p.returncode));(out/('command-'+str(len(report['attempts']))+'-private.log')).write_bytes(p.stdout+p.stderr);save();return p
def pm_sample(label):
 states={}
 for n in ['cam-front-vdig-k196','cam-front-vana-k196','ldo1']:
  for p in Path('/sys/class/regulator').glob('regulator.*'):
   if not (p/'name').exists() or (p/'name').read_text().strip()!=n:continue
   node=p/'of_node'
   if n=='ldo1' and (not node.exists() or not str(node.resolve()).endswith('/regulators-1/ldo1')):continue
   states[n]={key:(p/key).read_text().strip() for key in ['microvolts','num_users','state']}
 row=dict(label=label,sensor=sensor.joinpath('power/runtime_status').read_text().strip(),controller=Path('/sys/bus/platform/devices/ac4b000.cci/power/runtime_status').read_text().strip(),adapter=Path('/sys/bus/i2c/devices/i2c-7/power/runtime_status').read_text().strip() if Path('/sys/bus/i2c/devices/i2c-7/power/runtime_status').exists() else 'not-exposed',regulators=states);report['pm_observations'].append(row);save();return row
def video_fds():
 rows=[]
 for process in Path('/proc').iterdir():
  if not process.name.isdigit():continue
  try:
   for p in (process/'fd').iterdir():
    try:
     target=os.readlink(p)
     if target.startswith(('/dev/video','/dev/media','/dev/v4l-subdev')):rows.append(dict(pid=process.name,fd=p.name,target=target))
    except OSError:pass
  except OSError:pass
 return rows

def topology(label):
 rows=[]
 for device in sorted(Path('/dev').glob('media*')):
  p=subprocess.run(['media-ctl','-d',str(device),'-p'],capture_output=True,text=True,timeout=15);(out/(label+'-'+device.name+'-private.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0;rows.append(p.stdout)
 return '\n'.join(rows)

def rebind(bind):
 assert not video_fds()
 (camdriver/('bind' if bind else 'unbind')).write_text('acb3000.camss');time.sleep(.3)
 assert (camss/'driver').exists()==bind
 report['attempts'].append(dict(action='camss-bind' if bind else 'camss-unbind',returncode=0));save()

def capture_three(label):
 tool=root/'k197-offline-tools/front-capture-aarch64-private';tools=json.loads((root/'k197-offline-tools/manifest.json').read_text());assert hashlib.sha256(tool.read_bytes()).hexdigest()==next(r['sha256'] for r in tools if r['file']==tool.name)
 process=subprocess.Popen([str(tool),'--capture',str(out/(label+'-first-frame-private.raw'))],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 observed=[]
 def observe_active():
  for attempt in range(200):
   if process.poll() is not None:break
   pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text()
   if re.search(r'genpd:3:acb3000.camss\s+active\s+384\s',pd):
    clocks=Path('/sys/kernel/debug/clk/clk_summary').read_text();rows=[line.split() for line in clocks.splitlines() if 'cam_cc_ife_0_clk ' in line]
    if rows and int(rows[0][1])>0:
     (out/(label+'-active-genpd-private.txt')).write_text(pd);(out/(label+'-active-clocks-private.txt')).write_text(clocks);observed.append(True);break
   time.sleep(.002)
 thread=threading.Thread(target=observe_active);thread.start()
 try:stdout,stderr=process.communicate(timeout=40)
 finally:
  if process.poll() is None:process.terminate();stdout,stderr=process.communicate(timeout=10)
  thread.join(timeout=5);assert not thread.is_alive()
 (out/(label+'-capture-private.log')).write_bytes(stdout+stderr);assert process.returncode==0
 log=stdout.decode();frames=[]
 for m in re.finditer(r'FRAME number=(\d+) index=(\d+) sequence=(\d+) bytes=(\d+) changed=(\d+) active_bytes=(\d+) hash=[0-9a-f]+ timestamp_us=(\d+)',log):frames.append(dict(zip(['number','buffer','sequence','bytes','active_bytes_changed','active_bytes','timestamp_us'],map(int,m.groups()))))
 assert len(frames)==3 and 'PATTERNS sensor=0 csid=0 physical_link=enabled' in log and 'CAPTURE_RESULT success=1 cleanup_complete=1' in log
 report.setdefault('capture_cycles',[]).append(dict(label=label,frames=frames,active_performance_snapshot=bool(observed)));save();return frames

def idle(label):
 time.sleep(2);p=pm_sample(label);assert p['sensor']=='suspended' and (camss/'power/runtime_status').read_text().strip()=='suspended'
 pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();(out/(label+'-genpd-private.txt')).write_text(pd);assert re.search(r'genpd:3:acb3000.camss\s+suspended\s+0\s',pd);report.setdefault('idle_performance_dropped',[]).append(label);save()

def interrupt(signum,frame):raise RuntimeError('Interrupted; remove resources and restore saved state')
for sig in [signal.SIGINT,signal.SIGTERM,signal.SIGHUP]:signal.signal(sig,interrupt)
save()
assert not video_fds() and (camss/'driver').resolve()==camdriver;topology('original')
try:
 assert command(['insmod',str(stage/'samurai-front-overlay.ko')]).returncode==0
 assert (Path('/sys/bus/i2c/devices/1-0004')/'driver').resolve().name=='pm8008' and sensor.exists() and not (sensor/'driver').exists()
 assert int.from_bytes((sensor/'of_node/vif-supply').read_bytes(),'big')==live['vio_phandle'];report['resources_applied']=True;save()
 rebind(False);camss_refreshed=True
 rebind(True);report['persistent_candidate_rebound']=True;save()
 report['clock_lookup']={p.name:int(p.read_text()) for p in Path('/sys/module/samurai_front_overlay/parameters').iterdir()};save()
 event=tracefs/'events/i2c/i2c_reply'
 if event.exists() and (tracefs/'tracing_on').read_text().strip()=='0' and not (tracefs/'set_event').read_text().strip() and (event/'enable').read_text().strip()=='0':
  (out/'trace-before-private.txt').write_bytes((tracefs/'trace').read_bytes());old_filter=(event/'filter').read_text();(event/'filter').write_text('adapter_nr == 7');(tracefs/'trace').write_text('');(event/'enable').write_text('1');(tracefs/'tracing_on').write_text('1');traced=True
 assert command(['insmod',str(stage/'imx471.ko')]).returncode==0
 for wait_index in range(12):
  if (sensor/'driver').exists():break
  time.sleep(1)
 deferred=Path('/sys/kernel/debug/devices_deferred');(out/'deferred-private.txt').write_bytes(deferred.read_bytes() if deferred.exists() else b'no debugfs deferred file')
 (out/'sensor-uevent-private.txt').write_bytes((sensor/'uevent').read_bytes())
 report['sensor_links']={p.name:str(p.resolve()) for p in sensor.iterdir() if p.is_symlink()};save()
 assert (sensor/'driver').resolve().name=='imx471';report['normal_driver_bound']=True;report['physical_id_accepted_by_normal_driver']=True
 if traced:
  (tracefs/'tracing_on').write_text('0');(out/'probe-trace-private.txt').write_bytes((tracefs/'trace').read_bytes());(event/'enable').write_text('0');(event/'filter').write_text(old_filter if old_filter.strip()!='none' else '0');traced=False
 graph=topology('physical-before');assert 'imx471 7-0010' in graph;report['physical_media_graph_present']=True;pm_sample('before-capture');save()
 first=capture_three('first');idle('first-idle');second=capture_three('second');idle('second-idle');assert second[0]['timestamp_us']>first[-1]['timestamp_us'];report['frames']=first+second;report['physical_image_capture']=True;report['capture_returncode']=0;report['no_external_performance_helper']=not Path('/sys/module/samurai_camera_perf').exists();report['no_clock_rate_cap']=True;save()

finally:
 if traced:
  (tracefs/'tracing_on').write_text('0');(out/'probe-trace-private.txt').write_bytes((tracefs/'trace').read_bytes());(event/'enable').write_text('0');(event/'filter').write_text(old_filter if old_filter.strip()!='none' else '0')
 if camss_refreshed and (camss/'driver').exists():rebind(False)
 if Path('/sys/module/imx471').exists():assert command(['rmmod','imx471']).returncode==0
 if Path('/sys/module/samurai_front_overlay').exists():assert command(['rmmod','samurai_front_overlay']).returncode==0
 if camss_refreshed:rebind(True)
 if camss_refreshed:
  assert list(struct.unpack('>8I',Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/power-domains').read_bytes()))==live['original_camss_domains']
  topology('original-restored');report['camss_original_graph_restored']=True;save()
 assert not sensor.exists() and all(not Path('/sys/bus/i2c/devices/1-'+f'{a:04x}').exists() for a in [4,5])
 for n in ['qcom_pm8008','qcom_pm8008_regulator','v4l2_cci']:
  if Path('/sys/module/'+n).exists():assert command(['rmmod',n]).returncode==0
 current=snapshot(4);assert current['identity']==before['pmic']['identity'] and sample(0)==0 and sample(3)==1
 for old,new in zip(before['pmic']['ldos'],current['ldos']):
  base=0x4000+(old['index']-1)*0x100
  for name,offset in [('enable',0x46),('vset',0x40),('mode',0x45),('step',0x3b),('pull_down',0xa0)]:
   if old[name]['data']!=new[name]['data']:
    result=write(5,base+offset,old[name]['data']);report['register_restores'].append(result);save();assert result['success']
 report['pmic_after_restore']=snapshot(4);assert report['pmic_after_restore']==before['pmic']
 tlmm=Path('/sys/firmware/devicetree/base/soc@0/pinctrl@3100000');chips=[p for p in Path('/sys/bus/gpio/devices').glob('gpiochip*') if (p/'of_node').exists() and (p/'of_node').resolve()==tlmm];assert len(chips)==1;tfd=os.open('/dev/'+chips[0].name,os.O_RDONLY|os.O_CLOEXEC);memfd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC|os.O_CLOEXEC);after_gpios=[]
 for old in before['gpios']:
  info=bytearray(256);struct.pack_into('I',info,64,old['pin']);fcntl.ioctl(tfd,0xc100b405,info,True);assert not bytes(info[32:64]).rstrip(b'\0')
  req=bytearray(592);struct.pack_into('I',req,0,old['pin']);struct.pack_into('Q',req,288,4);struct.pack_into('I',req,560,1);fcntl.ioctl(tfd,0xc250b407,req,True);fd=struct.unpack_from('i',req,588)[0];value=level(fd);os.close(fd)
  with mmap.mmap(memfd,4096,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=old['ctl_address']) as mapping:ctl=struct.unpack_from('<I',mapping,0)[0]
  after_gpios.append(dict(pin=old['pin'],level=value,ctl=ctl,ctl_address=old['ctl_address']))
 os.close(memfd);os.close(tfd);report['gpios_after_restore']=after_gpios;save()
 for n in ['samurai_vio_phandle','samurai_cci_bringup','i2c_qcom_cci']:
  if Path('/sys/module/'+n).exists():assert command(['rmmod',n]).returncode==0
 assert hashlib.sha256(fw.read_bytes()).hexdigest()==overlay['dtbo_sha256'];fw.unlink();os.close(gfd);os.close(ifd);save()
after_log=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after_log);report['fault_delta']={k:after_log.count(v)-before_log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};report['taint']=int(Path('/proc/sys/kernel/tainted').read_text());report['pins_restored_exact']=all(a['pin']==b['pin'] and a['ctl']==b['ctl'] and a['level']==b['level'] for a,b in zip(report['gpios_after_restore'],before['gpios']));save()
assert report['pins_restored_exact'] and all(v==0 for v in report['fault_delta'].values()) and report['taint']==0
print(json.dumps({k:report.get(k) for k in ['stage','normal_driver_bound','physical_id_accepted_by_normal_driver','physical_media_graph_present','physical_image_capture','capture_returncode','camss_original_graph_restored','pins_restored_exact','fault_delta','taint']}))
