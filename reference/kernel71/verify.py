from pathlib import Path
import gzip, hashlib, json, re, runpy
r=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
exports=[]
for name,plain_len,gz_len in [('baseline-bootmeta',342,264),('touch-dmesg',54413,12775),
 ('touch-facts',1855,545),('touch-events',306744,43740),('touch-eventmeta',502,185),
 ('finish-dmesg',66932,14630),('finish-facts',956,480)]:
 m=json.loads((r/(name+'-validation.json')).read_text())
 data=(r/(name+'-received.gz')).read_bytes();body=gzip.decompress(data)
 assert sha(data)==m['device_sha256'] and len(data)==gz_len and len(body)==plain_len
 target='input-events.bin' if name=='touch-events' else name+'.validated.txt'
 assert body==(r/target).read_bytes(),name
 exports.append(dict(name=name,plain_bytes=plain_len,gzip_bytes=gz_len,sha256=sha(data),gzip_crc_pass=True))
observed=json.loads((r/'close-observations.json').read_text());captures=[]
for raw in sorted(r.glob('*.raw')):
 b=raw.read_bytes();pos=0;payload=bytearray();count=0
 while pos<len(b):
  assert b[pos]==0x90 and pos+2<=len(b),(raw.name,pos)
  n=b[pos+1];assert 1<=n<=4 and pos+2+n<=len(b),(raw.name,pos,n)
  payload.extend(b[pos+2:pos+2+n]);pos+=2+n;count+=1
 decoded=bytes(payload).decode('ascii',errors='replace').replace('\ufffd','?')
 assert decoded==(r/(raw.stem+'.txt')).read_bytes().decode('utf-8'),raw.name
 if raw.stem=='touch-f1-wsl':
  ev=[json.loads(x) for x in (r/'touch-f1-wsl.events.jsonl').read_text().splitlines()]
  assert any(x.get('event')=='receipt' and x.get('text')=='F1' for x in ev)
  assert observed['wsl']['resources_disposed_observed'] and observed['wsl']['finally_detach_attempted']
 else:
  o=observed['windows'][raw.stem];assert o['close_observed']
  if o['end_marker']: assert re.search('(?m)^'+o['end_marker']+'$',decoded.replace('\r',''))
  events=(r/(raw.stem+'.events.txt')).read_text()
  for line in events.splitlines():
   if 'TX native' in line and 'sync=False' in line:
    assert 'attempt=1' in line,line
    assert 'len=2 ' not in line,line
  if raw.stem=='touch-save':
   assert o['exit_code']==1 and 'sync=False' not in events
  if raw.stem=='touch-f1': assert count==0 and 'sent=1 receipt=False' in events
 captures.append(dict(name=raw.stem,frames=count,raw_bytes=len(b),decoded_payload_matches=True))
assert len(captures)==16
runpy.run_path(str(r/'validate-dtb.py'))
runpy.run_path(str(r/'analyze-input.py'))
inp=json.loads((r/'input-validation.json').read_text());assert inp['basic_touch_pass']
log=(r/'finish-dmesg.validated.txt').read_text()
assert log.startswith('[    0.000000]') and 'Synaptics, product: S3706A, fw id: 3078696' in log
assert 'input: Synaptics S3706A' in log and log.count('Attached SCSI disk')==6
assert not re.search('Kernel panic - not syncing|Oops:|WARNING:|BUG:',log)
assert not re.search('(?im)^.*(?:rmi4|c80000.i2c|gpi_dma).*?(?:error|failed|timed out|timeout)',log)
facts=(r/'finish-facts.validated.txt').read_text()
assert facts.startswith('a31c1158-fbca-4515-83ac-1a3b40ee808e\n0\n') and '#61 SMP' in facts
assert '\n1785600\n2419200\n2956800\n' in facts and '\na600000.usb\n' in facts
assert all(re.search('(?m)^'+disk+'$',facts) for disk in ('sda','sdb','sdc','sdd','sde','sdf'))
for i,(p,h) in enumerate(json.loads((r/'source-preservation.json').read_text()).items()):
 assert sha(gzip.decompress((r/f'preserved-source-{i}.gz').read_bytes()))==h,p
fw=json.loads((r/'firmware-validation.json').read_text())
assert fw['other_executable_bytes_unchanged'] and fw['compat_append_unchanged'] and fw['firmware_dtb_raw_section_matches']
fl=json.loads((r/'flash-validation.json').read_text())
assert {x['Partition'] for x in fl['images']}=={'boot','logdump'} and fl['flash_success']
assert not fl['userdata_written'] and not fl['gpt_written']
state=json.loads((r/'finish-state.json').read_text())
assert len(state['nodes'])==3 and all(n['Status']=='OK' for n in state['nodes'])
assert not state['known_owners'] and not state['known_linux_owners']
assert re.search(r'(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$',state['usbipd'])
assert state['temporary_logging_absent'] and not state['active_eud_trace']
assert state['driver_inf']=='oem102.inf' and state['driver_version']=='2.1.3.5'
if (r/'SHA256SUMS').exists():
 entries={}
 for line in (r/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);assert sha((r/n).read_bytes())==h,n;entries[n]=h
 assert set(entries)=={p.name for p in r.iterdir() if p.is_file() and p.name!='SHA256SUMS'}
report=dict(exports=exports,captures=captures,input=inp,firmware_audit_preserved=True,
            immutable_source_snapshots_pass=True,finish_state_released=True,
            no_new_touch_error_or_kernel_backtrace=True,whole_hardware_goal_complete=False)
(r/'verification-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Verified 7 exports, 16 raw captures, touch events, preserved sources and released finish state.')
