from pathlib import Path
import re

p=Path('/mnt/e/edk2-samurai-out/kernel190/mm-build/ModemManager-7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a/src/mm-shared-qmi.c')
lines=p.read_text().splitlines()
for start,count in [(6880,75),(7150,80)]:
    print('\n'.join('%d: %s'%(n+1,lines[n]) for n in range(start-1,min(start+count-1,len(lines)))))
for index,line in enumerate(lines):
    if any(term in line for term in ['INJECTION_REQUEST','INJECT_TIME_REQUEST','assistance_inject_time_req_indication_cb','inject-time-request','inject-utc-time-request','MM_LOCATION_SOURCE_GPS_UNMANAGED']):
        print('\n'.join('%d: %s'%(n+1,lines[n]) for n in range(max(0,index-3),min(len(lines),index+8))))
