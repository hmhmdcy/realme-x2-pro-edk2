"""Finite CPU ISP comparison; retain and reject growth of the recorded GPU warnings."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
proof=json.loads((here/'system-heap-capture-validation.json').read_text())
assert proof['taint']==512 and proof['fault_delta']['warning']==349 and proof['cma_node_original_mode_restored']
code=(here/'capture-user-libcamera.py').read_text().replace("root/'k211-user-libcamera'","root/'k211-user-libcamera-cpu'").replace("runtime/'samurai-camera-211'","runtime/'samurai-camera-211-cpu'")
code=code.replace("assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'", "assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'\nknown_log=subprocess.check_output(['dmesg'])\nknown_warnings=[line for line in known_log.splitlines() if b'WARNING:' in line]\nassert len(known_warnings)==349 and all(b'__arm_lpae_unmap' in line and b'drivers/iommu/io-pgtable-arm.c:673' in line for line in known_warnings)\nassert known_log.count(b'Oops:')==known_log.count(b'gpu fault:')==known_log.count(b'fatal error received')==known_log.count(b'Frame reassembly failed')==0")
code=code.replace("'LIBCAMERA_LOG_LEVELS':'*:INFO'","'LIBCAMERA_LOG_LEVELS':'*:INFO,DmaBufAllocator:DEBUG','LIBCAMERA_SOFTISP_MODE':'cpu'")
code=code.replace("process=subprocess.Popen(args,","args=['/usr/sbin/strace','-f','-yy','-e','trace=openat,ioctl','-o',str(output/'cpu-trace-private.txt')]+args\nprocess=subprocess.Popen(args,")
code+=r'''
shutil.copy2(output/'cpu-trace-private.txt',out/'cpu-trace-private.txt')
trace=(out/'cpu-trace-private.txt').read_text(errors='replace')
report['explicit_cpu_isp']=True
report['previous_gpu_unmap_warning_count_preserved']=len(known_warnings)
report['no_drm_device_opened']='/dev/dri/' not in trace
report['no_egl_renderer_in_log']=not any(s in stderr.decode(errors='replace') for s in ['GL_RENDERER','EGL_VERSION','DebayerEGL'])
report['allocator_debug']=[line for line in stderr.decode(errors='replace').splitlines() if 'DmaBufAllocator' in line]
report['new_faults_zero']=not any(faults.values())
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'cpu_isp_comparison':report}))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100)
(host.PRIVATE/'cpu-isp-capture-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout.splitlines()[-1])['cpu_isp_comparison']
(here/'cpu-isp-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
