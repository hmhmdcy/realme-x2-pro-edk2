from pathlib import Path
import json,re
import host

target=host.PRIVATE/'first-good-uart-trace-private.txt';host.download('/var/lib/samurai/k205-uart-reprobe/1-uart-trace-private.txt',target)
lines=target.read_text().splitlines();pairs=[]
for i,line in enumerate(lines):
 if 'geni_serial_tx_data:' not in line:continue
 m=re.search(r'data=([0-9a-fA-F ]+)',line)
 if not m:continue
 raw=bytes.fromhex(m[1])
 if len(raw)==5 and raw[:4]==bytes([1,0x48,0xfc,1]):
  after=[]
  for other in lines[i+1:]:
   if 'geni_serial_rx_data:' not in other:continue
   match=re.search(r'data=([0-9a-fA-F ]+)',other)
   if match:
    data=bytes.fromhex(match[1]);after.append(dict(bytes=len(data),packet_type=data[0] if data else None,first_four_protocol_bytes=list(data[:4])))
   if len(after)==3:break
  pairs.append(dict(baud_request_payload=raw[4],following_rx=after))
r=dict(stage=205,good_trace_baud_transactions=len(pairs),transactions=pairs,raw_uart_data_retained_private=True)
(host.PRIVATE/'good-uart-protocol-summary-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
