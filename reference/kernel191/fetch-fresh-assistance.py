from pathlib import Path
import hashlib,json,urllib.parse,urllib.request
import host
root=host.PRIVATE/'assistance';root.mkdir(exist_ok=True)
code=b'''import dbus,json
bus=dbus.SystemBus(private=True)
p=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
loc=p.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(loc['SupportedAssistanceData'])==1 and int(loc['Enabled'])==0
print(json.dumps([str(s) for s in loc['AssistanceDataServers']]));bus.close()
'''
p=host.ssh('python3 -',input=code);servers=json.loads(p.stdout);assert servers
(root/'servers-private.json').write_text(json.dumps(servers));records=[]
for index,server in enumerate(servers):
 parsed=urllib.parse.urlsplit(server);assert parsed.scheme in ['http','https'] and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
 url=urllib.parse.urlunsplit(('https',parsed.netloc,parsed.path,'',''))
 try:
  with urllib.request.urlopen(url,timeout=40) as response:data=response.read(5*1024*1024+1);headers=dict(response.headers)
  assert 0<len(data)<=5*1024*1024 and not data.lstrip().lower().startswith((b'<html',b'<!doctype'))
  (root/'xtra-private.bin').write_bytes(data);(root/'headers-private.json').write_text(json.dumps(headers))
  records.append(dict(index=index,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),tls=True,downloaded=True));break
 except Exception as e:records.append(dict(index=index,downloaded=False,error_type=type(e).__name__))
assert records[-1]['downloaded']
report=dict(stage=191,results=records,advertised_global_urls_only=True,no_query_credentials_or_fragment=True,no_device_location_or_identifiers_sent=True)
(Path(__file__).resolve().parent/'assistance-download-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
