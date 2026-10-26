from pathlib import Path
import ast
R=Path(__file__).resolve().parent
text=(R.parent/'kernel237/native-capture-r2.py').read_text()
text=text.replace("assert (which,kind) in [('rear','raw'),('front','raw'),('front','rgb')]","assert (which,kind)==('rear','raw')")
text=text.replace("out=root/f'k237-capture-{which}-{kind}-r2'","out=root/'k238-controlled-rear-r14'").replace('stage=237','stage=238')
text=text.replace("save();process=None;","trace=None;trace_removed=False;maps_seen=set();save();process=None;")
text=text.replace("env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG')", "prefix=Path('/run/samurai-camera238-r14')\n env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG',LD_LIBRARY_PATH=str(prefix/'usr/lib'),XDG_CONFIG_HOME=str(prefix/'config-enabled'),LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa'))")
text=text.replace("'/run/samurai-camera237-probes/native-physical-probe'","'/run/samurai-camera238-probes/physical-control-probe'")
marker=" save('finite-physical-capture')"
assert text.count(marker)==1
text=text.replace(marker,""" set_controls(sensor,{'digital_gain':256,'vertical_blanking':2126})
 trace=Path('/sys/kernel/tracing/instances/k238_controls');assert not trace.exists();trace.mkdir()
 (trace/'tracing_on').write_text('0');(trace/'events/enable').write_text('0');(trace/'buffer_size_kb').write_text('1024');(trace/'trace_clock').write_text('mono')
 event=trace/'events/i2c/i2c_write';form=(event/'format').read_text();assert all(k+';' in form for k in ['adapter_nr','addr','msg_nr','len','flags'])
 (event/'filter').write_text('adapter_nr == 7 && addr == 16 && msg_nr == 0 && len == 4 && flags == 0');assert 'parse_error' not in (event/'filter').read_text()
 (event/'enable').write_text('1');(trace/'tracing_on').write_text('1')
 save('controlled-48-frame-capture-trace-armed')""")
text=text.replace(" state['capture_pid']=process.pid;save()", """ state['capture_pid']=process.pid;save()
 for _ in range(10):
  if process.poll() is not None:break
  try:
   mapped=Path('/proc',str(process.pid),'maps').read_text()
   for line in mapped.splitlines():
    if '/run/samurai-camera238-r14/' in line:maps_seen.add(line.split()[-1])
  except OSError:pass
  time.sleep(.1)
 (out/'candidate-mapped-files-private.json').write_text(json.dumps(sorted(maps_seen),indent=2)+'\\n')""")
text=text.replace('process.communicate(timeout=25)','process.communicate(timeout=65)')
text=text.replace(" (out/'stdout-private.json').write_bytes(stdout);(out/'stderr-private.txt').write_bytes(stderr)",""" (out/'stdout-private.json').write_bytes(stdout);(out/'stderr-private.txt').write_bytes(stderr)
 if trace is not None and trace.exists():
  attempt('trace-stop',lambda:(trace/'tracing_on').write_text('0'))
  attempt('trace-disable',lambda:(trace/'events/enable').write_text('0'))
  attempt('trace-save',lambda:(out/'i2c-control-trace-private.txt').write_text((trace/'trace').read_text()))
  for statfile in trace.glob('per_cpu/cpu*/stats'):
   attempt('trace-stats:'+statfile.parent.name,lambda p=statfile:(out/(p.parent.name+'-trace-stats-private.txt')).write_text(p.read_text()))
  attempt('trace-remove',lambda:trace.rmdir());trace_removed=not trace.exists()""")
text=text.replace("  sensor_csid_patterns_zero=", "  raw_cpu_statistics_log=b'RAW-only CPU statistics enabled' in stderr, candidate_core_and_ipa_mapped=all(any('/run/samurai-camera238-r14/usr/lib/'+name in p for p in maps_seen) for name in ['libcamera.so','libcamera-base.so','libcamera/ipa/ipa_soft_simple.so']),trace_instance_removed=trace_removed,explicit_exposure_gain_phases=True,\n  sensor_csid_patterns_zero=")
text=text.replace('len(frames)==6','len(frames)==48').replace("'mclk1_mclk2_disabled']","'mclk1_mclk2_disabled','raw_cpu_statistics_log','candidate_core_and_ipa_mapped','trace_instance_removed']")
ast.parse(text);assert 'k238-controlled-rear-r14' in text and 'len(frames)==48' in text
(R/'native-controlled-capture.py').write_text(text)
print('Prepared one exact rear48-frame r14 candidate experiment with control-write tracing')
