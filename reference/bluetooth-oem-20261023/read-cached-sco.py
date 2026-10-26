from pathlib import Path
import json,struct
base=Path('/mnt/e/edk2-samurai-out/kernel185')
paths=[base/'before-reboot-evidence-private'/n/'hci-monitor-private.jsonl' for n in ['k185-scan-before','k185-scan-before-v2','k185-scan-after']]+[base/'final-evidence-private'/n/'hci-monitor-private.jsonl' for n in ['k185-scan-after-suspend','k185-scan-postresume']]
summary=[]
for p in paths:
 results=[];opcounts={}
 for line in p.read_text().splitlines():
  r=json.loads(line);data=bytes.fromhex(r['packet']);op,idx,n=struct.unpack_from('<HHH',data)
  opcounts[op]=opcounts.get(op,0)+1
  if op!=3:continue
  e=data[6:]
  if len(e)<5 or e[0]!=0x0e:continue
  cmd=struct.unpack_from('<H',e,3)[0];ret=e[5:]
  if cmd==0x1005 and len(ret)>=8:
   status,acl_len,sco_len,acl_n,sco_n=struct.unpack_from('<BHBHH',ret)
   results.append(dict(command='ReadBufferSize',status=status,acl_mtu=acl_len,sco_mtu=sco_len,acl_packets=acl_n,sco_packets=sco_n))
  if cmd==0x1002 and len(ret)>=65:results.append(dict(command='ReadLocalSupportedCommands',enhanced_setup_sync=bool(ret[30]&8),enhanced_accept_sync=bool(ret[30]&16)))
 summary.append({'evidence_window':p.parent.name,'results':results,'sco_tx_monitor_packets':opcounts.get(6,0),'sco_rx_monitor_packets':opcounts.get(7,0)})
 print(p.parent.name,json.dumps({'results':results,'packet_type_counts':opcounts}))

report={'source':'existing stage185 private HCI monitor capture; no new handset operation','monitor_header':'little-endian opcode,index,length; targeted Command Complete decoding only','enhanced_sync_supported_commands':'byte29 bits3/4 after status byte','windows':summary,'does_not_prove_actual_sco_audio_or_hci_route':True,'identifiers_addresses_and_other_payloads_omitted':True}
(Path(__file__).parent/'cached-sco-summary.json').write_text(json.dumps(report,indent=2)+'\n')
