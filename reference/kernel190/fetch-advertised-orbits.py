"""Fetch advertised global GNSS assistance over TLS, without publishing device data."""
from pathlib import Path
import hashlib,json,urllib.parse,urllib.request
import host

root=host.PRIVATE/'assistance-data-private';root.mkdir(exist_ok=True)
path=root/'servers-private.json';host.download('/var/lib/samurai/k190-orbit-order/servers-private.json',path)
servers=json.loads(path.read_text());assert isinstance(servers,list) and servers
results=[]
for index,server in enumerate(servers):
 parsed=urllib.parse.urlsplit(server)
 assert parsed.scheme in ['http','https'] and parsed.hostname and not parsed.username and not parsed.password
 assert not parsed.query and not parsed.fragment
 url=urllib.parse.urlunsplit(('https',parsed.netloc,parsed.path,parsed.query,''))
 try:
  with urllib.request.urlopen(url,timeout=30) as response:
   data=response.read(5*1024*1024+1);headers=dict(response.headers)
  assert 0<len(data)<=5*1024*1024
  dest=root/('server-'+str(index)+'-data-private.bin');dest.write_bytes(data)
  (root/('server-'+str(index)+'-headers-private.json')).write_text(json.dumps(headers))
  record=dict(server_index=index,downloaded=True,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),tls_used=True)
  results.append(record);break
 except Exception as error:
  results.append(dict(server_index=index,downloaded=False,error_type=type(error).__name__))
(root/'download-results-private.json').write_text(json.dumps(results,indent=2)+'\n')
(Path(__file__).resolve().parent/'assistance-download-validation.json').write_text(json.dumps(dict(results=results,device_location_or_identifiers_sent=False),indent=2)+'\n')
print(json.dumps(results))
