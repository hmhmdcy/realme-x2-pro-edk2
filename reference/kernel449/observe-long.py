from pathlib import Path
import json,shlex,sys
import host
attempt=sys.argv[1] if len(sys.argv)>1 else 'r2';assert attempt in ['r1','r2','r3']
code=r'''from pathlib import Path
import json,re
root=Path(ROOT);s=json.loads((root/'state.json').read_text());result=dict(phase=s['phase'],terminal=s['terminal'])
def live(pid):
 try:return Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
 except OSError:return False
result['worker_live']=live(s['pid']);result['fixture_live']=live(s.get('client_pid',-1))
if s['terminal']:
 result.update(passed=s['passed'],sustained=s.get('sustained',{}))
elif s['phase'].startswith('capture-user-'):
 case=s['phase'].removeprefix('capture-');path=root/case/'client.log'
 with path.open('rb') as f:
  f.seek(max(0,path.stat().st_size-131072));tail=f.read().decode(errors='replace')
 frames=re.findall(r'GST_IMAGE frame=(\d+).*sequence=(\d+) wall-ns=(\d+)',tail)
 if frames:result.update(consumed_frames=int(frames[-1][0])+1,last_sof=int(frames[-1][1]))
 try:children=Path('/proc',str(s['client_pid']),'task',str(s['client_pid']),'children').read_text().split()
 except OSError:
  children=[]
  for candidate in Path('/proc').glob('[0-9]*'):
   try:
    fields=(candidate/'stat').read_text().rsplit(')',1)[1].split()
    if int(fields[1])==s['client_pid']:children.append(candidate.name)
   except OSError:pass
 apps=[]
 for pid in children:
  p=Path('/proc',pid)
  try:
   args=[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]
   if args and Path(args[0]).name=='gst-sustained':apps.append(p)
  except OSError:pass
 if len(apps)==1:
  p=apps[0];status=dict(line.split(':',1) for line in (p/'status').read_text().splitlines() if ':' in line)
  assert all(int(v)==10000 for v in status['Uid'].split()) and int(status['CapEff'].strip(),16)==0
  maps=(p/'maps').read_text();expected='/run/user/10000/k449-user-'+ATTEMPT+'-'+case+'/lib/libcamera.so.0.7.2';assert expected in maps
  result.update(uid=10000,effective_capabilities=0,actual_candidate_core_mapping=True,application_pid=int(p.name),rss_kb=int(status['VmRSS'].split()[0]),hwm_kb=int(status['VmHWM'].split()[0]))
  ipa={int(v) for v in re.findall(r'IPA stats pid=(\d+)',tail)}
  if len(ipa)==1:
   ip=Path('/proc',str(next(iter(ipa))));data=dict(line.split(':',1) for line in (ip/'status').read_text().splitlines() if ':' in line)
   assert all(int(v)==10000 for v in data['Uid'].split()) and int(data['CapEff'].strip(),16)==0
   result['actual_isolated_ipa_uid10000_capabilities0']=next(iter(ipa))!=int(p.name)
print(json.dumps(result))
'''.replace('ROOT',repr('/var/lib/samurai/k449-lifecycle-user-'+attempt)).replace('ATTEMPT',repr(attempt))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode();data=json.loads(q.stdout)
i=1
while (host.PRIVATE/f'live-{attempt}-{i}-private.json').exists():i+=1
(host.PRIVATE/f'live-{attempt}-{i}-private.json').write_bytes(q.stdout);print(json.dumps(data,indent=2))
