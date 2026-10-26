"""Inspect static symbols/strings of the exact stock HAL, never load its code."""
from pathlib import Path
import json,re,subprocess
import host
P=host.PRIVATE;binary=P/'hal-source/camera.qcom.so'
q=subprocess.run(['aarch64-linux-gnu-readelf','--dyn-syms','--wide','--demangle',str(binary)],capture_output=True,text=True,check=True)
(P/'hal-symbols.txt').write_text(q.stdout)
symbols=[line for line in q.stdout.splitlines() if re.search(r'EEPROM|Checksum|CheckSum|check_sum|CRC',line)]
q=subprocess.run(['strings','-t','x',str(binary)],capture_output=True,text=True,check=True)
strings=[line for line in q.stdout.splitlines() if re.search(r'checksum|check_sum|fx319|WB.*[Cc]heck|LSC.*[Cc]heck|EEPROM.*valid',line,re.I)]
(P/'hal-eeprom-symbols.json').write_text(json.dumps({'symbols':symbols,'strings':strings},indent=2)+'\n')
print(json.dumps({'symbols':symbols[:20],'integrity_strings':strings[:32],'symbol_count':len(symbols),'string_count':len(strings)},indent=2))
