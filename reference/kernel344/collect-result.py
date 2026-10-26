from pathlib import Path
import json,re,shlex,sys
import host

HERE=Path(__file__).resolve().parent;P=host.PRIVATE
d=json.loads((P/'probe-r1-observation.json').read_text());assert d['state']['terminal'] and not d['worker_live']
summary=d['state']['summary'];iq=json.loads((HERE/'default-iq-validation.json').read_text())
gst=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',d['logs'].get('installed-gstreamer.log',''))
pw=re.search(r'PW_RESULT frames=(\d+) format-accepted=(\d+) errors=(\d+) result=(\d+)',d['logs'].get('installed-pipewire.log',''))
code='''
from pathlib import Path
import json
result={}
for name,pids in SERVICES.items():
 rows=[]
 for pid in pids:
  p=Path('/proc',str(pid));live=p.exists() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
  if not live:rows.append(dict(pid=pid,live=False));continue
  paths=sorted({line.split(None,5)[5].strip() for line in (p/'maps').read_text().splitlines() if len(line.split(None,5))==6 and ('libcamera' in line or 'ipa_camss' in line)})
  env=dict(x.decode().split('=',1) for x in (p/'environ').read_bytes().split(b'\\0') if x)
  rows.append(dict(pid=pid,live=True,uid=p.stat().st_uid,camera_library_paths=paths,library_path_override=env.get('LD_LIBRARY_PATH')))
 result[name]=rows
print(json.dumps(dict(services=result,private_profiles_present={model:(Path('/etc/libcamera/ipa/camss-vfe')/(model+'.yaml')).is_file() for model in ['s5kgw1','imx471','imx319','s5k3m5']})))
'''.replace('SERVICES',repr(summary['services']))
if '--reuse-service-observation' in sys.argv:
 previous=json.loads((HERE/'install-r1-validation.json').read_text())
 actual=dict(services=previous['final_services'],private_profiles_present=previous['private_profiles_present'])
 if not (HERE/'service-host-assumption-r1.json').exists():
  (HERE/'service-host-assumption-r1.json').write_text(json.dumps(dict(previous,reason='Initial collector assumed the camera SPA lived in pipewire; actual maps identify wireplumber as its host'),indent=2)+'\n')
else:actual=json.loads(host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
services_ok=all(len(rows)==1 and rows[0]['live'] and rows[0]['uid']==10000 for rows in actual['services'].values())
spa_hosts=[dict(service=name,**row) for name,rows in actual['services'].items() for row in rows if any('/libspa-libcamera.so' in path for path in row.get('camera_library_paths',[]))]
packaged_core_mapped=bool(spa_hosts) and all('/usr/lib/libcamera.so.0.7.2' in row['camera_library_paths'] and '/usr/lib/libcamera/ipa/ipa_camss_vfe.so' in row['camera_library_paths'] for row in spa_hosts)
report=dict(stage=344,transaction=summary,default_iq_passed=iq['passed'],
 hardware_cameras=d['logs'].get('enumeration.log','').count('for pipeline handler camss-vfe'),
 pipewire_camera_nodes=len(re.findall(r'PW_NODE id=',d['logs'].get('pw-enumeration.log',''))),
 gstreamer=dict(frames=int(gst[1]),width=int(gst[2]),height=int(gst[3]),errors=int(gst[4]),result=int(gst[5])) if gst else None,
 pipewire=dict(frames=int(pw[1]),format_accepted=bool(int(pw[2])),errors=int(pw[3]),result=int(pw[4])) if pw else None,
 final_services=actual['services'],private_profiles_present=actual['private_profiles_present'],camera_spa_hosts=spa_hosts,packaged_core_and_ipa_mapped_by_spa_host=packaged_core_mapped,
 spa_private_profile_path_log_available=any('/etc/libcamera/ipa/camss-vfe/' in d['logs'].get('new-'+row['service']+'.log','') for row in spa_hosts),normal_light_optical_calibration=False)
report['passed']=bool(summary['passed'] and iq['passed'] and services_ok and packaged_core_mapped and all(actual['private_profiles_present'].values()) and
 report['hardware_cameras']==4 and report['pipewire_camera_nodes']==4 and gst and pw and int(gst[1])>0 and not int(gst[4]) and not int(gst[5]) and int(pw[1])>0 and int(pw[2]) and not int(pw[3]) and not int(pw[4]))
(HERE/'install-r1-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='transaction'},indent=2));assert report['passed']
