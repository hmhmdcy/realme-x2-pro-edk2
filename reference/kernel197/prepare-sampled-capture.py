from pathlib import Path
ref=Path(__file__).resolve().parent
s=(ref/'prepare-diagnostic-live-native.py').read_text().replace('k197-live-prepare-r4','k197-live-prepare-r5');(ref/'prepare-sampled-live-native.py').write_text(s)
s=(ref/'capture-front-diagnostic-session.py').read_text().replace('k197-front-capture-r4','k197-front-capture-r5').replace('k197-live-prepare-r4','k197-live-prepare-r5')
old="capture=subprocess.run([str(tool),'--capture',str(out/'first-frame-private.raw')],capture_output=True,timeout=40);"
new='''import threading
 process=subprocess.Popen([str(tool),'--capture',str(out/'first-frame-private.raw')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 def sample_active_clocks():
  saved=0;attempts=0;rows=[]
  while process.poll() is None and attempts<150:
   attempts+=1
   clocks=Path('/sys/kernel/debug/clk/clk_summary').read_bytes()
   hits=[line.split() for line in clocks.decode().splitlines() if 'cam_cc_ife_0_csid_clk ' in line]
   if hits and int(hits[0][1])>0 and saved<3:
    saved+=1;(out/('active-'+str(saved)+'-clocks-private.txt')).write_bytes(clocks)
    for label,path in [('genpd','/sys/kernel/debug/pm_genpd/pm_genpd_summary'),('interrupts','/proc/interrupts')]:
     if Path(path).exists():(out/('active-'+str(saved)+'-'+label+'-private.txt')).write_bytes(Path(path).read_bytes())
    rows.append(dict(sample=saved,monotonic=time.monotonic(),csid_clock_line=hits[0][:10]))
   time.sleep(.01)
  (out/'active-clock-sampler-private.json').write_text(json.dumps(dict(attempts=attempts,samples=rows),indent=2)+'\\n')
 thread=threading.Thread(target=sample_active_clocks);thread.start()
 try:
  stdout,stderr=process.communicate(timeout=40)
 finally:
  if process.poll() is None:process.terminate();stdout,stderr=process.communicate(timeout=10)
  thread.join(timeout=5);assert not thread.is_alive()
 capture=subprocess.CompletedProcess(process.args,process.returncode,stdout,stderr);'''
assert old in s;s=s.replace(old,new);(ref/'capture-front-sampled-session.py').write_text(s)
for attempt,folder in [('third','r4'),('fourth','r5')]:
 s=(ref/'finalize-second-capture-attempt.py').read_text().replace('k197-front-capture-r3','k197-front-capture-'+folder);(ref/('finalize-'+attempt+'-capture-attempt.py')).write_text(s)
print('Prepared active-clock observation during one bounded capture attempt')
