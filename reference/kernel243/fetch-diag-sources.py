"""Fetch primary protocol sources to private cache; never execute them."""
from pathlib import Path
import hashlib,json,urllib.request
P=Path('/mnt/e/edk2-samurai-out/kernel243');O=P/'protocol-sources';O.mkdir(mode=0o700,exist_ok=True)
def get(url):
 return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'GNSS-port-research'}),timeout=25).read()
targets={
 'mi-log_packet.h':'https://raw.githubusercontent.com/mobile-insight/mobileinsight-core/master/dm_collector_c/log_packet.h',
 'mi-gnss_gps_measurement_report.h':'https://raw.githubusercontent.com/mobile-insight/mobileinsight-core/master/dm_collector_c/gnss_gps_measurement_report.h',
 'mi-gnss_glonass_measurement_report.h':'https://raw.githubusercontent.com/mobile-insight/mobileinsight-core/master/dm_collector_c/gnss_glonass_measurement_report.h',
 'mi-log_packet.cpp':'https://raw.githubusercontent.com/mobile-insight/mobileinsight-core/master/dm_collector_c/log_packet.cpp',
 'openpilot-tree.json':'https://api.github.com/repos/commaai/openpilot/git/trees/0f40ca1d?recursive=1',
}
manifest={}
for name,url in targets.items():
 try:
  p=O/name
  if not p.exists():p.write_bytes(get(url))
  b=p.read_bytes();manifest[name]=dict(url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),ok=True)
 except Exception as e:manifest[name]=dict(url=url,ok=False,error=type(e).__name__)
tree=O/'openpilot-tree.json'
if tree.exists():
 candidates=[x['path'] for x in json.loads(tree.read_text())['tree'] if 'qcomgps' in x['path'] and x['path'].endswith('.py')]
 print(json.dumps(dict(openpilot_sources=candidates)),flush=True)
 for path in candidates:
  if Path(path).name not in ['modemdiag.py','structs.py','qcomgpsd.py']:continue
  name='openpilot-'+Path(path).name;url='https://raw.githubusercontent.com/commaai/openpilot/0f40ca1d/'+path
  try:
   b=get(url);(O/name).write_bytes(b);manifest[name]=dict(url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),ok=True)
  except Exception as e:manifest[name]=dict(url=url,ok=False,error=type(e).__name__)
(P/'protocol-source-manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))
