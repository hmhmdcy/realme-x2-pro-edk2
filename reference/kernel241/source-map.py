from pathlib import Path
import json,re,subprocess
from elfview import Elf
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel241')
V=Path('/mnt/e/edk2-samurai-out/kernel238/vendor-source-private/payload/lib64')
F=Path('/mnt/e/edk2-samurai-out/kernel238/vendor-followup-source-private/payload/lib64')
header=Path('/mnt/e/edk2-samurai-out/kernel221/loc-upstream/location_service_v02.h').read_text()
names={}
for name,number in re.findall(r'#define\s+(QMI_LOC_\w+)\s+0x([0-9A-Fa-f]+)\b',header):
    names.setdefault(int(number,16),[]).append(name)
calls=json.loads((P/'qmi-calls-private.json').read_text())
loc=Elf(V/'libloc_api_v02.so')
report=[]
for item in calls:
    id=item['message_id']
    label=next((n for n in names.get(id,[]) if '_REQ' in n),next(iter(names.get(id,[])),None))
    report.append(dict(address='0x'+item['call_address'],message_id=id,hex_id=hex(id) if id is not None else None,
                       public_idl_name=label,containing_export=loc.describe(int(item['call_address'],16))))
(P/'qmi-message-map-private.json').write_text(json.dumps(report,indent=2)+'\n')
for item in report:print(item['address'],item['hex_id'],item['public_idl_name'])
for lib in [V/'libloc_core.so',F/'liblbs_core.so',V/'libgnss.so']:
    e=Elf(lib)
    for s in e.syms:
        if re.search('injectFeatureConfig|setFeatureConfig|readConfig|::isMaster|powerState|PowerState|setPremium|PIP|SAP|injectXtra',s['demangled']):
            print(lib.name,hex(s['value']),s['size'],s['shndx'],s['demangled'])
            if s['shndx'] and re.search('injectFeatureConfig|::isMaster',s['demangled']):
                asm=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','-C','--start-address='+str(s['value']),'--stop-address='+str(s['value']+s['size']),str(lib)],text=True)
                (P/(lib.name+'-'+hex(s['value'])+'-private.txt')).write_text(asm)
