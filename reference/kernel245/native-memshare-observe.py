"""Bounded MEMSHARE request observation; no physical allocation or DMA handoff.

Publish the OEM service/version/instance for 110 seconds. GPS query-size may
return the OEM board's zero initial size. Any allocation/free request returns
QMI failure, never a physical address. Keep all request payloads private.
"""
from pathlib import Path
import collections,dbus,hashlib,json,os,select,signal,socket,struct,subprocess,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');o=r/'k245-memshare-observe';assert not o.exists();o.mkdir(mode=0o700)
state=dict(stage=245,state='preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().split()[21]);s=None;bus=None;child=None;published=False;withdrawn=False;failure=None;requests=[];responses=0;malformed=0;raw_records=0
def save():
 p=o/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(o/'state-private.json')
def stop(signum,frame):raise KeyboardInterrupt('Memshare observation interrupted')
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);save()
def ns(command,instance):
 node,port=s.getsockname();s.sendto(struct.pack('<IIIII',command,52,instance,node,port),(node,0xfffffffe))
def tlvs(data):
 result={};off=0
 while off<len(data):
  assert len(data)-off>=3;t,n=struct.unpack_from('<BH',data,off);off+=3;assert off+n<=len(data) and t not in result;result[t]=data[off:off+n];off+=n
 return result
def item(t,b):return struct.pack('<BH',t,len(b))+b
def u32(values,t):
 assert t in values and len(values[t])==4;return struct.unpack('<I',values[t])[0]
def poll(timeout,log,observe=False):
 global raw_records,responses,malformed
 if not select.select([s],[],[],timeout)[0]:return
 b,anc,flags,peer=s.recvmsg(65536);assert not flags&socket.MSG_TRUNC;raw_records+=1;assert raw_records<=1024 and len(b)<=4096
 log.write(json.dumps(dict(elapsed_ms=round((time.monotonic()-began)*1000),peer=list(peer),hex=b.hex()))+'\n');log.flush()
 if peer[1]==0xfffffffe:
  if len(b)==20:
   cmd,service,instance,node,port=struct.unpack('<IIIII',b)
   if not observe and cmd==4 and service==52:raise RuntimeError('A MEMSHARE service already exists; do not replace it')
  return
 if not observe or peer[0]!=0:return
 try:
  assert len(b)>=7;kind,txn,msg,n=struct.unpack_from('<BHHH',b);assert kind==0 and n==len(b)-7;v=tlvs(b[7:]);row=dict(message_id=msg,tlv_lengths={hex(k):len(x) for k,x in v.items()})
  body=item(2,struct.pack('<HH',1,2)) # FAILURE / NO_MEMORY, zero handles
  if msg==0x22:
   row.update(requested_bytes=u32(v,1),client_id=u32(v,2),proc_id=u32(v,3),sequence_id=u32(v,4));body+=item(0x10,v[4]);row['response']='no_memory'
   if 0x10 in v:assert len(v[0x10])==1;row['contiguous']=v[0x10][0]
   if 0x11 in v:row['block_alignment']=u32(v,0x11)
  elif msg==0x24:
   row.update(client_id=u32(v,1),proc_id=u32(v,0x10) if 0x10 in v else None)
   if row['client_id']==0 and row['proc_id'] in [None,0]:body=item(2,struct.pack('<HH',0,0))+item(0x10,struct.pack('<I',0));row['response']='gps_initial_size_zero'
   else:row['response']='no_memory'
  else:row['response']='no_memory_no_physical_access'
  s.sendto(struct.pack('<BHHH',2,txn,msg,len(body))+body,peer);responses+=1;requests.append(row);state.update(state='observing',request_count=len(requests),message_counts=dict(collections.Counter(hex(x['message_id']) for x in requests)));save()
 except (AssertionError,struct.error):malformed+=1;raise
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 for attempt in ['k245-resume-rf','k245-resume-rf-r2','k245-resume-rf-r3','k245-resume-rf-r4']:
  st=json.loads((r/attempt/'state-private.json').read_text());assert st['terminal']
 pid=int(Path('/run/samurai-wifi/rmtfs.pid').read_text());assert hashlib.sha256(Path('/proc',str(pid),'exe').read_bytes()).hexdigest()=='d1ca1fc4087e47f1618e09f568605f2f253eac8721598fc930d1eb8c604fe251'
 check=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True,timeout=20);(o/'nv-before-private.txt').write_bytes(check.stdout+check.stderr);assert check.returncode==0
 before=subprocess.check_output(['dmesg']);(o/'dmesg-before-private.txt').write_bytes(before);pkg=Path('/lib/apk/db/installed').read_bytes()
 bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();path=next(str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',path),'org.freedesktop.DBus.Properties');loc_before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');power_before=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));watch=json.loads((r/'gnss-assist/watch-state.json').read_text());assert int(loc_before['Enabled'])==0 and not loc_before['SignalsLocation'] and not watch['active'] and watch['time_prepared'] and not bus.name_has_owner('org.freedesktop.GeoClue2')
 tools=r/'k226-loc-tools-r3';binary=tools/'loc-session';build=json.loads((tools/'build-summary.json').read_text());assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256'] and build['fixed_observation_seconds']==90 and build['message_allowlist']==[33,34,35,50,51,63,75]
 sys.path.insert(0,str(r/'k245-tools'));from loc_decode import summarize
 s=socket.socket(42,socket.SOCK_DGRAM);s.bind((s.getsockname()[0],0));began=time.monotonic()
 with (o/'memshare-events-private.jsonl').open('x') as log:
  ns(10,0);end=time.monotonic()+3
  while time.monotonic()<end:poll(min(0.25,end-time.monotonic()),log,False)
  # OEM QMI service 52, version 1, instance 1 => raw QRTR instance 0x101.
  ns(4,0x101);published=True;state.update(state='published_no_allocation',request_count=0);save();end=time.monotonic()+10
  while time.monotonic()<end:poll(min(0.25,end-time.monotonic()),log,True)
  with (o/'loc-events-private.jsonl').open('xb') as out,(o/'loc-stderr-private.txt').open('xb') as err:
   env=dict(os.environ);env.pop('LD_PRELOAD',None);env.pop('LD_LIBRARY_PATH',None);child=subprocess.Popen([str(binary),'high'],stdout=out,stderr=err,env=env);state.update(state='gnss_running',child_pid=child.pid);save();deadline=time.monotonic()+170
   try:
    while child.poll() is None:
     if time.monotonic()>deadline:raise RuntimeError('GNSS deadline')
     poll(0.25,log,True)
   finally:
    if child.poll() is None:child.terminate();child.wait(timeout=40)
  rows=[json.loads(x) for x in (o/'loc-events-private.jsonl').read_text().splitlines()];cleanup=rows[-1];assert child.returncode==0 and cleanup['kind']=='cleanup' and all(cleanup[k] for k in ['stop_ack','client_released','device_closed']);decoded=summarize(rows);assert not decoded['decode_errors']
  end=time.monotonic()+7
  while time.monotonic()<end:poll(min(0.25,end-time.monotonic()),log,True)
  ns(5,0x101);withdrawn=True;s.close();s=None
 after=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after);loc_after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');watch_after=json.loads((r/'gnss-assist/watch-state.json').read_text());check=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True,timeout=20);(o/'nv-after-private.txt').write_bytes(check.stdout+check.stderr);assert check.returncode==0
 report=dict(stage=245,service=52,version=1,instance=1,requests=requests,response_count=responses,malformed_requests=malformed,raw_records=raw_records,elapsed_seconds=round(time.monotonic()-began,2),physical_allocations=0,physical_addresses_returned=0,dma_or_scm_ownership_changes=0,server_withdrawal_sent=withdrawn,socket_closed=s is None,receiver=decoded,cleanup=cleanup,original_nv_sources_preserved=True,location_preserved=all(loc_before[k]==loc_after[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate']),power_preserved=power_before==int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState')),watch_preserved=not watch_after['active'] and all(watch[k]==watch_after[k] for k in ['worker_starts','worker_completions']),package_db_preserved=pkg==Path('/lib/apk/db/installed').read_bytes(),fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()))
 (o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');assert report['location_preserved'] and report['power_preserved'] and report['watch_preserved'] and report['package_db_preserved'] and report['taint']==0 and not any(report['fault_delta'].values());state.update(state='terminal',terminal=True,exit_code=0);save()
except BaseException:
 failure=traceback.format_exc();(o/'failure-private.txt').write_text(failure)
finally:
 try:
  if child is not None and child.poll() is None:child.terminate();child.wait(timeout=40)
  if s:
   if published:ns(5,0x101);withdrawn=True
   s.close();s=None
 except BaseException:(o/'cleanup-failure-private.txt').write_text(traceback.format_exc());failure=failure or 'cleanup failure'
 if bus:bus.close()
 if failure:state.update(state='failed',terminal=child is None or child.poll() is not None,exit_code=1,server_withdrawal_sent=withdrawn,socket_closed=s is None);save()
if failure:raise SystemExit(1)
