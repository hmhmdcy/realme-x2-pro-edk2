from pathlib import Path
import concurrent.futures,datetime,email.utils,hashlib,json,time,urllib.parse,urllib.request
import host

ref=Path(__file__).resolve().parent;out=host.PRIVATE/'assistance';assert not out.exists();out.mkdir(mode=0o700)
code=b'''from pathlib import Path
import dbus,json,subprocess,time
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k201-baseline/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(loc['Enabled'])==0 and int(loc['SupportedAssistanceData'])==1
p=subprocess.run(['chronyc','-n','tracking'],capture_output=True,text=True);tracking=p.stdout+p.stderr
Path('/var/lib/samurai/k201-baseline/clock-tracking-private.txt').write_text(tracking)
print(json.dumps(dict(servers=[str(s) for s in loc['AssistanceDataServers']],phone_epoch=time.time(),chrony_normal='Leap status     : Normal' in tracking,mm_gps_enabled=0)));bus.close()
'''
start=time.time();p=host.ssh('python3 -',input=code,timeout=25);end=time.time();state=json.loads(p.stdout)
(out/'servers-and-clock-private.json').write_text(json.dumps(state,indent=2)+'\n');assert abs(state['phone_epoch']-(start+end)/2)<10
before=json.loads((ref/'validity-before-validation.json').read_text());assert before['ack'] and before['indication'] and before['status']==0
epoch=state['phone_epoch'];valid_from=before['start_utc_timestamp'];valid_until=valid_from+before['duration_hours']*3600
age=dict(valid_from_utc=datetime.datetime.fromtimestamp(valid_from,datetime.timezone.utc).isoformat(),valid_until_utc=datetime.datetime.fromtimestamp(valid_until,datetime.timezone.utc).isoformat(),phone_utc=datetime.datetime.fromtimestamp(epoch,datetime.timezone.utc).isoformat(),currently_valid=valid_from<=epoch<valid_until,expired_seconds=max(0,epoch-valid_until),chrony_normal=state['chrony_normal'],timestamp_units_confirmed_by_qcom_aosp_header=True,source='https://android.googlesource.com/platform/hardware/qcom/gps/+/android-4.2.2_r1/loc_api/loc_api_v02/location_service_v02.h')
(ref/'orbit-current-validity-validation.json').write_text(json.dumps(age,indent=2)+'\n')

def fetch(pair):
 index,server=pair;parsed=urllib.parse.urlsplit(server)
 assert parsed.scheme in ['http','https'] and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
 url=urllib.parse.urlunsplit(('https',parsed.netloc,parsed.path,'',''))
 try:
  request=urllib.request.Request(url,headers={'Cache-Control':'no-cache','Pragma':'no-cache'})
  with urllib.request.urlopen(request,timeout=35) as response:
   final=urllib.parse.urlsplit(response.url);assert final.scheme=='https' and not final.query and not final.fragment
   data=response.read(5*1024*1024+1);headers=dict(response.headers)
  assert 0<len(data)<=5*1024*1024 and not data.lstrip().lower().startswith((b'<html',b'<!doctype'))
  (out/('server-'+str(index)+'-private.bin')).write_bytes(data);(out/('server-'+str(index)+'-headers-private.json')).write_text(json.dumps(headers,indent=2))
  lower={k.lower():v for k,v in headers.items()}
  return dict(server_index=index,downloaded=True,tls=True,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),date=lower.get('date'),last_modified=lower.get('last-modified'),cache_age=lower.get('age'),same_as_old191=hashlib.sha256(data).hexdigest()=='e905a7291990c20324210b3bb405d84f8088da283f969255e2b28e34676d4008')
 except Exception as error:return dict(server_index=index,downloaded=False,error_type=type(error).__name__)

servers=state['servers'];assert len(servers)==3
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:records=list(pool.map(fetch,enumerate(servers)))
report=dict(stage=201,firmware_validity=age,downloads=records,advertised_global_urls_only=True,no_query_credentials_fragment_or_device_data_sent=True,no_cache_request_headers=True,no_data_injected=True)
(ref/'assistance-refresh-download-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
