"""Read the installed sensor integration and retained matching SSC source."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R.parent/'kernel268/host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import json,subprocess,re
result={};source=Path('/var/lib/samurai/k184-libssc-r2/source/libssc')
result['ssc_sources']={}
for p in source.glob('src/*'):
 if p.is_file() and any(x in p.name for x in ['accel','sensor.c','sensor-private']):result['ssc_sources'][p.name]=p.read_text(errors='replace')
result['proxy_files']=subprocess.run(['apk','info','-L','iio-sensor-proxy'],capture_output=True,text=True).stdout
result['package_records']={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 row={l[:1]:l[2:] for l in block.splitlines() if len(l)>2 and l[1]==':'}
 if row.get('P') in ['iio-sensor-proxy','phosh','libssc']:result['package_records'][row['P']]={k:row[k] for k in ['V','o','c','U'] if k in row}
result['config_sources']={}
for p in [Path('/etc/xdg/iio-sensor-proxy.conf'),Path('/etc/conf.d/iio-sensor-proxy'),Path('/etc/udev/hwdb.d/61-sensor-local.hwdb')]:
 if p.is_file():result['config_sources'][str(p)]=p.read_text()
print(json.dumps(result))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=25);(P/'rotation-sources-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
print(json.dumps(dict(package_records=d['package_records'],retained_ssc_sources=list(d['ssc_sources']),configuration_sources=d['config_sources']),indent=2))
for n,s in d['ssc_sources'].items():
 print(n)
 for i,l in enumerate(s.splitlines()):
  if any(x in l.lower() for x in ['mount','matrix','orientation','accel','value','event->data']):print(str(i+1)+':'+l)
