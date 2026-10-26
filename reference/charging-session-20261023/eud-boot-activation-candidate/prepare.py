"""Offline-only generation; never imports or executes either handset worker."""
from pathlib import Path
import ast,difflib,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parents[1]/'charging-oem-audit-20261023/normal-restart-candidate'
SOURCES={'quiesce':(OLD/'r7-quiesce-review.py','f991d580bc587423c8ee85d0412d8a75480ee6f6b37a7f8413dc0c9f4b3a17b4'),
 'restart':(OLD/'transport-tail-audit/r7-restart-transport-tail-review.py','f7cfc985b0caf5694b59d24af3c5100942faa48c9a8b783e02a102abf87dc615')}
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def once(s,old,new):
 assert s.count(old)==1,old
 return s.replace(old,new,1)

def transform(kind,source):
 start=source.index('# NEW contract:')
 marker="assert sys.argv[3]=='--commit-quiesce'" if kind=='quiesce' else "assert sys.argv[3] in ['--inspect','--commit-restart2-bootloader']"
 end=source.index(marker)
 guard=(HERE/'guard-fragment.py').read_text()
 result=source[:start]+guard+'\n'+source[end:]
 result=result.replace("work='charging-r7-restart'","work='eud-boot-activation'")
 result=result.replace("transaction_id=meta['transaction_id'],boot_id=meta['boot_id']","transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],token=meta['token']")
 result=result.replace('# REVIEW CANDIDATE ONLY. New R7 transaction; same validated hardware quiesce.', '# UNRUN EUD BOOT ACTIVATION CANDIDATE. Same validated hardware quiesce.')
 if kind=='restart':
  result=once(result,"assert (before&255) in [0,1]","assert before in (0,1,0x01010101)")
  result=once(result,"assert struct.unpack_from('<I',csr,0x14)[0]&255==0","assert struct.unpack_from('<I',csr,0x14)[0]==0")
  result=once(result,"assert s['transaction_id']==proof['transaction_id']==meta['transaction_id']","assert s['transaction_id']==proof['transaction_id']==meta['transaction_id']\nassert s['token']==proof['token']==meta['token']")
  result=once(result,"with phase.open('x') as claim:json.dump(dict(transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],token=meta['token'],state='claimed_once',request_count=1),claim)","with phase.open('x') as claim:\n   json.dump(dict(transaction_id=meta['transaction_id'],boot_id=meta['boot_id'],token=meta['token'],state='claimed_once',request_count=1),claim);claim.flush();os.fsync(claim.fileno())\n  phase_parent=os.open(phase.parent,os.O_RDONLY|os.O_DIRECTORY)\n  try:os.fsync(phase_parent)\n  finally:os.close(phase_parent)")
 ast.parse(result)
 return result

def main():
 result={'offline_generation_only':True,'workers_executed':False,'files':{}}
 for kind,(path,digest) in SOURCES.items():
  raw=path.read_bytes();assert sha(raw)==digest
  source=raw.decode().replace('\r\n','\n');candidate=transform(kind,source)
  name='eud-'+kind+'.py';target=HERE/name;target.write_text(candidate,encoding='utf-8',newline='\n')
  (HERE/(name+'.patch')).write_text(''.join(difflib.unified_diff(source.splitlines(True),candidate.splitlines(True),fromfile=str(path),tofile=name)),encoding='utf-8',newline='\n')
  result['files'][name]={'source_sha256':digest,'candidate_sha256':sha(target.read_bytes())}
 result['guard_sha256']=sha((HERE/'guard-fragment.py').read_bytes())
 (HERE/'generation-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2))

if __name__=='__main__':main()
