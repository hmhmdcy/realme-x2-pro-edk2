from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent
proof=json.loads((here/'runtime-validation.json').read_text());assert proof['taint']==0 and proof['same_boot211_image_second_warm_boot']
code=(here.parent/'kernel211/capture-user-libcamera.py').read_text().replace('k211','k212').replace('camera-211','camera-212').replace('stage=211','stage=212').replace("'--capture=3'","'--capture=6'").replace('three_rgb_frames_captured','six_rgb_frames_captured').replace('len(frames)==3','len(frames)==6')
retry=sys.argv[1:]==['--r2'];assert not sys.argv[1:] or retry
if retry:code=code.replace("root/'k212-user-libcamera'","root/'k212-user-libcamera-r2'").replace("runtime/'samurai-camera-212'","runtime/'samurai-camera-212-r2'")
code=code.replace("process=subprocess.Popen(args,","args=['/usr/sbin/strace','-f','-yy','-e','trace=openat,ioctl','-o',str(output/'cpu-trace-private.txt')]+args\nprocess=subprocess.Popen(args,")
code+=r'''
shutil.copy2(output/'cpu-trace-private.txt',out/'cpu-trace-private.txt')
trace=(out/'cpu-trace-private.txt').read_text(errors='replace')
report['no_cpu_mode_environment_override']='LIBCAMERA_SOFTISP_MODE' not in env
report['system_configuration_opened']=bool(re.search(r'openat\([^\n]+"/etc/libcamera/configuration.yaml"[^\n]+\) = [0-9]+',trace))
report['no_drm_device_opened']='/dev/dri/' not in trace
report['no_egl_renderer_in_log']=not any(s in stderr.decode(errors='replace') for s in ['GL_RENDERER','EGL_VERSION','DebayerEGL'])
report['post_warmup_four_rgb_frames_nonconstant']=len(frames)==6 and all(f['nonconstant'] for f in frames[2:])
report['black_startup_frame_indices']=[i for i,f in enumerate(frames) if not f['nonconstant']]
report['stream_configuration']=[line for line in stderr.decode(errors='replace').splitlines() if 'configuring streams:' in line or 'SoftwareIsp' in line]
report['allocator_debug']=[line for line in stderr.decode(errors='replace').splitlines() if 'DmaBufAllocator' in line]
report['new_faults_zero']=not any(faults.values())
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'default_cpu_capture':report}))
'''
suffix='-r2' if retry else ''
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/('default-cpu-capture'+suffix+'-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout.splitlines()[-1])['default_cpu_capture'];(here/('default-cpu-capture'+suffix+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
