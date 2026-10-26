from pathlib import Path
import hashlib,json,host
here=Path(__file__).resolve().parent;canonical=here.parents[1]/'linux-port/camera';dest='/var/lib/samurai/k211-heap-stage'
host.ssh('test ! -e '+dest+' && mkdir -m700 '+dest)
manifest={}
for name in ['samurai-camera-heaps.conf','70-samurai-camera-heaps.rules']:
    p=canonical/name;manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest();host.upload(p,dest+'/'+name)
p=host.PRIVATE/'heap-source-manifest.json';p.write_text(json.dumps(manifest,indent=2)+'\n');host.upload(p,dest+'/source-manifest.json');host.upload(here/'install-heaps.py',dest+'/install-heaps.py')
p=host.ssh('python3 '+dest+'/install-heaps.py',timeout=90);(host.PRIVATE/'heap-deploy-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'heap-deployment-validation.json').write_text(json.dumps(report,indent=2)+'\n')
plan=json.loads((host.PRIVATE/'current-work-private.json').read_text());plan.update(state='211 heap modules loaded; standard OpenRC autoload config and video/uaccess rule deployed. UID10000 allocation/map/sync/readback/close verified; no sensor streaming or transition.',next='Finish mode-register-derived crop state and return fix, build/install compatible imx471 module; verify actual libcamera/user capture and warm boot persistence.')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report))
