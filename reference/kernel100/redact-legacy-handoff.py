from pathlib import Path
import json, re

root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel100')
path=root/'HANDOVER-NEXT.md'
text=path.read_text()
serial=json.loads((out/'fastboot-identity.json').read_text())['serial']
text,count=re.subn(re.escape(serial),'PRIVATE_DEVICE_ID',text,flags=re.I)
profile=(out.parent/'kernel95/wpa-test-private.conf').read_text()
wifi_count=0
for value in re.findall(r'^\s*#?\s*(?:psk|ssid)\s*=\s*(.+?)\s*$',profile,re.M):
    text,n=re.subn(re.escape(value.strip('"')),'PRIVATE_WIFI_VALUE',text,flags=re.I)
    wifi_count+=n
text,mac_count=re.subn(r'(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}','PRIVATE_MAC',text)
path.write_text(text)
(out/'legacy-handoff-redaction.json').write_text(json.dumps(dict(serial_occurrences=count,wifi_occurrences=wifi_count,
    mac_occurrences=mac_count,original_private_copy='public-docs-before.json'),indent=2)+'\n')
print('LEGACY_HANDOFF_IDENTITIES_REDACTED')
