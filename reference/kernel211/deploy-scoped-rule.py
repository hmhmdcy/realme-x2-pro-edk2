from pathlib import Path
import host,json
here=Path(__file__).resolve().parent;dest='/var/lib/samurai/k211-heap-stage'
host.upload(here.parents[1]/'linux-port/camera/70-samurai-camera-heaps.rules',dest+'/70-samurai-camera-heaps-scoped.rules')
p=host.ssh('python3 -',input=(here/'refine-heap-access.py').read_bytes(),timeout=70);(host.PRIVATE/'heap-refine-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'heap-access-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
