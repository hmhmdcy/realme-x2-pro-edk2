from pathlib import Path
import json,re,struct,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();rows=[json.loads(x) for x in (r/'k244-nextboot/capture/diag-events-private.jsonl').read_text().splitlines()]
feature=next(x for x in rows if x['kind']=='rx' and x.get('channel')==0 and bytes.fromhex(x['hex'])[:4]==struct.pack('<I',8));peer=(feature['node'],feature['port']);markers={}
for name in ['tftp','rmtfs']:
 text=Path('/run/samurai-wifi',name+'.log').read_text();pattern=r'\bdel_client(?: for)?\s+'+str(peer[0])+':'+str(peer[1])+r'\b';markers[name]=len(re.findall(pattern,text))
dmesg=subprocess.check_output(['dmesg']).decode();boots=[line for line in dmesg.splitlines() if 'Booting fw image' in line and '/modem.mdt' in line]
print(json.dumps({'report':dict(stage=245,observed_control_peer_delete_matches=markers,modem_boot_messages=len(boots),current_boot_matches_seed=(r/'k244-nextboot/capture/boot-id-private.txt').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes()),'private':dict(peer=peer,modem_boot_messages=boots)}))
