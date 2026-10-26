from pathlib import Path
import re
o=Path('/mnt/e/edk2-samurai-out/kernel109')
t=(o/'wifi-scan-diagnostic-private.txt').read_text(encoding='utf-8-sig')
for line in t.splitlines():
    if any(w in line for w in ['CTRL-EVENT','nl80211','failed','firmware crashed','fatal','scan failed','Key deletion','SME:','timed out']):
        line=re.sub(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}','[address]',line)
        line=re.sub(r"(?i)ssid\s*=\s*(?:'[^']*'|\"[^\"]*\")",'SSID=[private]',line)
        print(line)
rows=[l for l in t.splitlines() if re.match(r'(?:[a-f0-9]{2}:){5}',l)]
print('scan_result_count='+str(len(rows)))
print('scan_frequencies='+str(sorted(set(re.findall(r'^\S+\s+(\d{4})\s+-?\d+\s',t,re.M)))))
