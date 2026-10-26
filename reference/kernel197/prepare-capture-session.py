from pathlib import Path
ref=Path(__file__).resolve().parent
s=(ref.parent/'kernel196/probe-front-driver-r6.py').read_text().replace('k196','k197').replace('stage=196','stage=197').replace('k197-front-probe-r6','k197-front-capture')
s=s.replace('/lib/firmware/samurai/k197-front.dtbo','/lib/firmware/samurai/k196-front.dtbo').replace('cam-front-vdig-k197','cam-front-vdig-k196').replace('cam-front-vana-k197','cam-front-vana-k196')
s=s.replace('sensor=Path(\'/sys/bus/i2c/devices/7-0010\')',"sensor=Path('/sys/bus/i2c/devices/7-0010');camss=Path('/sys/bus/platform/devices/acb3000.camss');camdriver=Path('/sys/bus/platform/drivers/qcom-camss');camss_refreshed=False")
marker='def interrupt(signum,frame):'
helpers='''def video_fds():
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
 return '\\n'.join(rows)

def rebind(bind):
 assert not video_fds()
 (camdriver/('bind' if bind else 'unbind')).write_text('acb3000.camss');time.sleep(.3)
 assert (camss/'driver').exists()==bind
 report['attempts'].append(dict(action='camss-bind' if bind else 'camss-unbind',returncode=0));save()

'''
s=s.replace(marker,helpers+marker)
s=s.replace("save()\ntry:\n", "save()\nassert not video_fds() and (camss/'driver').resolve()==camdriver;topology('original')\ntry:\n",1)
s=s.replace("report['clock_lookup']=", "rebind(False);camss_refreshed=True;rebind(True)\n report['clock_lookup']=",1)
start=s.index(" first=pm_sample('after-probe-idle')")
end=s.index('\nfinally:',start)
s=s[:start]+''' graph=topology('physical-before');assert 'imx471 7-0010' in graph;report['physical_media_graph_present']=True;pm_sample('before-capture');save()
 tool=root/'k197-offline-tools/front-capture-aarch64-private';tools=json.loads((root/'k197-offline-tools/manifest.json').read_text());assert hashlib.sha256(tool.read_bytes()).hexdigest()==next(r['sha256'] for r in tools if r['file']==tool.name)
 capture=subprocess.run([str(tool),'--capture',str(out/'first-frame-private.raw')],capture_output=True,timeout=40);(out/'capture-private.log').write_bytes(capture.stdout+capture.stderr);report['capture_returncode']=capture.returncode;save();assert capture.returncode==0
 import re
 log=capture.stdout.decode();frames=[]
 for m in re.finditer(r'FRAME number=(\\d+) index=(\\d+) sequence=(\\d+) bytes=(\\d+) changed=(\\d+) active_bytes=(\\d+) hash=[0-9a-f]+ timestamp_us=(\\d+)',log):frames.append(dict(zip(['number','buffer','sequence','bytes','active_bytes_changed','active_bytes','timestamp_us'],map(int,m.groups()))))
 assert len(frames)==3 and 'PATTERNS sensor=0 csid=0 physical_link=enabled' in log and 'CAPTURE_RESULT success=1 cleanup_complete=1' in log
 report['frames']=frames;report['physical_image_capture']=True;time.sleep(2);pm_sample('after-capture');topology('physical-after');save()
''' +s[end:]
s=s.replace(" if Path('/sys/module/imx471').exists():", " if camss_refreshed and (camss/'driver').exists():rebind(False)\n if Path('/sys/module/imx471').exists():",1)
s=s.replace(" assert not sensor.exists() and all(", " if camss_refreshed:rebind(True);topology('original-restored');report['camss_original_graph_restored']=True;save()\n assert not sensor.exists() and all(",1)
s=s[:s.index('print(json.dumps(dict(stage=197')]+"print(json.dumps({k:report.get(k) for k in ['stage','normal_driver_bound','physical_id_accepted_by_normal_driver','physical_media_graph_present','physical_image_capture','capture_returncode','frames','camss_original_graph_restored','pins_restored_exact','fault_delta','taint']}))\n"
(ref/'capture-front-session.py').write_text(s)
print('Prepared bounded physical capture session with CAMSS cleanup')
