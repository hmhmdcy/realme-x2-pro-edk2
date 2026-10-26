from pathlib import Path
ref=Path(__file__).resolve().parent;s=(ref/'capture-front-mmcx.py').read_text();s=s.replace('import hashlib,json,mmap,os,shutil,subprocess,time','import hashlib,json,mmap,os,re,shutil,subprocess,threading,time')
s=s.replace("assert snapshot(4)==before['pmic']", "assert not Path('/sys/module/samurai_camera_perf').exists()\nassert snapshot(4)==before['pmic']",1)
marker='def interrupt(signum,frame):'
functions='''def capture_three(label):
 tool=root/'k197-offline-tools/front-capture-aarch64-private';tools=json.loads((root/'k197-offline-tools/manifest.json').read_text());assert hashlib.sha256(tool.read_bytes()).hexdigest()==next(r['sha256'] for r in tools if r['file']==tool.name)
 process=subprocess.Popen([str(tool),'--capture',str(out/(label+'-first-frame-private.raw'))],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 observed=[]
 def observe_active():
  for attempt in range(200):
   if process.poll() is not None:break
   pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text()
   if re.search(r'genpd:3:acb3000.camss\\s+active\\s+384\\s',pd):
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
 for m in re.finditer(r'FRAME number=(\\d+) index=(\\d+) sequence=(\\d+) bytes=(\\d+) changed=(\\d+) active_bytes=(\\d+) hash=[0-9a-f]+ timestamp_us=(\\d+)',log):frames.append(dict(zip(['number','buffer','sequence','bytes','active_bytes_changed','active_bytes','timestamp_us'],map(int,m.groups()))))
 assert len(frames)==3 and 'PATTERNS sensor=0 csid=0 physical_link=enabled' in log and 'CAPTURE_RESULT success=1 cleanup_complete=1' in log
 report.setdefault('capture_cycles',[]).append(dict(label=label,frames=frames,active_performance_snapshot=bool(observed)));save();return frames

def idle(label):
 time.sleep(2);p=pm_sample(label);assert p['sensor']=='suspended' and (camss/'power/runtime_status').read_text().strip()=='suspended'
 pd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();(out/(label+'-genpd-private.txt')).write_text(pd);assert re.search(r'genpd:3:acb3000.camss\\s+suspended\\s+0\\s',pd);report.setdefault('idle_performance_dropped',[]).append(label);save()

'''
assert marker in s;s=s.replace(marker,functions+marker)
start=s.index(" tool=root/'k197-offline-tools/front-capture-aarch64-private'",s.index(" graph=topology('physical-before')"));end=s.index('\nfinally:',start)
s=s[:start]+''' first=capture_three('first');idle('first-idle');second=capture_three('second');idle('second-idle');assert second[0]['timestamp_us']>first[-1]['timestamp_us'];report['frames']=first+second;report['physical_image_capture']=True;report['capture_returncode']=0;report['no_external_performance_helper']=not Path('/sys/module/samurai_camera_perf').exists();report['no_clock_rate_cap']=True;save()
'''+s[end:]
s=s.replace("if camss_refreshed:topology('original-restored');", "if camss_refreshed:\n  assert list(struct.unpack('>6I',Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/power-domains').read_bytes()))==live['original_camss_domains']\n  topology('original-restored');")
(ref/'capture-front-mmcx-repeat.py').write_text(s);print('Prepared two independent physical capture cycles with idle performance checks')
