"""One finite diagnostic: withhold CMA from the user, restore modes in finally."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
capture=(here/'capture-user-libcamera.py').read_text().replace("root/'k211-user-libcamera'","root/'k211-user-libcamera-system'").replace("runtime/'samurai-camera-211'","runtime/'samurai-camera-211-system'").replace("'LIBCAMERA_LOG_LEVELS':'*:INFO'","'LIBCAMERA_LOG_LEVELS':'*:INFO,DmaBufAllocator:DEBUG'")
code="""from pathlib import Path
import json,os,stat
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='suspended'
node=Path('/dev/dma_heap/reserved');saved=stat.S_IMODE(node.stat().st_mode)
assert saved==0o660
try:
    os.chmod(node,0o600)
    exec(CAPTURE)
finally:
    os.chmod(node,saved)
assert stat.S_IMODE(node.stat().st_mode)==saved
report['cma_node_original_mode_restored']=True
report['diagnostic_cma_node_temporarily_root_only']=True
report['allocator_debug']=[line for line in stderr.decode(errors='replace').splitlines() if 'DmaBufAllocator' in line]
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps({'system_heap_diagnostic':report}))
""".replace('CAPTURE',repr(capture))
p=host.ssh('python3 -',input=code.encode(),timeout=100)
(host.PRIVATE/'system-heap-capture-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout.splitlines()[-1])['system_heap_diagnostic']
(here/'system-heap-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
