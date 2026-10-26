"""Validate startup timing, exact QMI request and observer response receipt."""
from pathlib import Path
import json,struct
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k247-runtime/boot-id-private.txt').read_bytes();o=r/'k247-nextboot/capture';a=json.loads((o/'summary.json').read_text());events=[json.loads(x) for x in (o/'memshare-events-private.jsonl').read_text().splitlines()];published=next(x for x in events if x['kind']=='memshare_published');confirmed=next(x for x in events if x['kind']=='memshare_publication_confirmed');requests=[]
for x in events:
 if x['kind']=='rx' and x['peer'][0]==0 and x['peer'][1]!=0xfffffffe:
  b=bytes.fromhex(x['hex']);kind,txn,msg,n=struct.unpack_from('<BHHH',b);assert kind==0 and len(b)==7+n
  assert msg==0x24 and n==14 and b[7:]==bytes.fromhex('0104000100000010040000000000')
  requests.append(dict(message_id=hex(msg),client_id=1,proc_id=0,bytes=len(b),published_before_request=x['monotonic_ns']>published['monotonic_ns'],namespace_readback_before_request=x['monotonic_ns']>confirmed['monotonic_ns']))
assert len(requests)==a['memshare']['request_count']==a['memshare']['response_count']==1 and all(x['published_before_request'] for x in requests)
dm=(o/'dmesg-after-publication-private.txt').read_bytes();after=(o/'dmesg-after-private.txt').read_bytes();match=lambda data:[line for line in data.splitlines() if b'Booting fw image' in line and b'/modem.mdt' in line]
assert not match(dm) and len(match(after))==1
reply=[x['request'] for x in events if x['kind']=='request_response'];assert len(reply)==1 and reply[0]['response_result']==1 and reply[0]['response_error']==41
cleanup=events[-1];assert cleanup['kind']=='memshare_cleanup' and cleanup['withdrawal_sent'] and cleanup['socket_closed'] and not cleanup['error']
report=dict(stage=247,namespace_publication_independently_confirmed=True,no_linux_modem_boot_log_at_publication=True,one_linux_modem_boot_log_afterward=True,requests=requests,response=dict(result=1,error=41,configured_client_not_implemented=True),startup_gps_client_requests=0,allocation_requests=0,observer_duration_seconds=a['elapsed_seconds'],closed_and_withdrawn=True,no_physical_allocation_or_scm=True,not_a_complete_oem_memshare_emulation=True,absence_of_gps_request_does_not_exclude_dependency_on_client1=True)
print(json.dumps(dict(report=report)))
