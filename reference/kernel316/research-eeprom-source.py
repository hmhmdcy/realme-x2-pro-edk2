"""Locate OEM integrity hooks using cached inventory and a pinned source file."""
from pathlib import Path
import hashlib,json,re,urllib.request
import host
P=host.PRIVATE
inventory=json.loads((P.parent/'kernel298/oem-tuning-inventory-private.json').read_text())
print('EEPROM vendor objects:',[x['path'] for x in inventory['files'] if 'eeprom' in x['path'].lower()])
cache=P/'calibration-sources';cache.mkdir(exist_ok=True)
p=cache/'camxeepromdata.cpp'
if not p.exists():
 url='https://raw.githubusercontent.com/comprehensive9/vendor_qcom_proprietary/36fc163a534963a5b3af52186af5efcc63401ad2/camx/src/core/camxeepromdata.cpp'
 p.write_bytes(urllib.request.urlopen(url,timeout=30).read())
assert hashlib.sha256(p.read_bytes()).hexdigest()=='660d47fbaee9b3ed5bec8da9a94c183799bef3f6e43ffdc00aa72d0b2090a7a7'
lines=p.read_text().splitlines();matches=[]
for i,line in enumerate(lines):
 if re.search(r'checksum|CheckCRC|CustomFormat|EEPROMLibraryAPI|isCustom',line,re.I):
  matches.append((i+1,'\n'.join(lines[max(0,i-2):i+5])))
for i,text in matches[:22]:print('line',i,text)
(P/'eeprom-source-hook-summary.json').write_text(json.dumps({'source_commit':'36fc163a534963a5b3af52186af5efcc63401ad2','matches':[n for n,_ in matches],'checksum_verified':False,'unit_values_applied':False},indent=2)+'\n')
