from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=(here/'capture-user-libcamera.py').read_text().replace("root/'k211-user-libcamera'","root/'k211-user-libcamera-trace'").replace("runtime/'samurai-camera-211'","runtime/'samurai-camera-211-trace'")
code=code.replace("'LIBCAMERA_LOG_LEVELS':'*:INFO'","'LIBCAMERA_LOG_LEVELS':'*:INFO,DmaBufAllocator:DEBUG,SoftwareIsp:DEBUG'")
code=code.replace("process=subprocess.Popen(args,","args=['/usr/sbin/strace','-f','-yy','-e','trace=openat,ioctl','-o',str(output/'dma-trace-private.txt')]+args\nprocess=subprocess.Popen(args,")
code=code.replace("images=out/'images-private';", "shutil.copy2(output/'dma-trace-private.txt',out/'dma-trace-private.txt')\nimages=out/'images-private';")
code += r'''
lines=(out/'dma-trace-private.txt').read_text(errors='replace').splitlines()
selected=[line for line in lines if '/dev/dma_heap/' in line]
report['dma_heap_trace']=selected
report['cma_pools']={p.name:{f.name:f.read_text().strip() for f in p.iterdir() if f.name in ['count','used','maxchunk','base_pfn']} for p in Path('/sys/kernel/debug/cma').glob('*') if p.is_dir()}
report['allocator_debug']=[line for line in stderr.decode(errors='replace').splitlines() if 'DmaBufAllocator' in line or 'SoftwareIsp' in line]
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'trace_detail':report}))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100)
(host.PRIVATE/'user-capture-trace-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout.splitlines()[-1])['trace_detail']
report['cma_pools']={k:{a:b for a,b in v.items() if a!='base_pfn'} for k,v in report['cma_pools'].items()}
(here/'user-libcamera-trace-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
