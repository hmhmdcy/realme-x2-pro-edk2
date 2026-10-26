from pathlib import Path
import re

base=Path('/mnt/e/edk2-samurai-out/kernel190/mm-build/ModemManager-7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a/src')
for name in ['mm-broadband-modem-qmi.c','mm-iface-modem.c']:
    lines=(base/name).read_text().splitlines()
    selected=set()
    for index,line in enumerate(lines):
        if re.search(r'power_down|power_off|OPERATING_MODE_LOW_POWER|OPERATING_MODE_SHUTTING_DOWN',line):
            selected.update(range(max(0,index-3),min(len(lines),index+12)))
    print(name)
    for index in sorted(selected):print('%d: %s'%(index+1,lines[index]))
