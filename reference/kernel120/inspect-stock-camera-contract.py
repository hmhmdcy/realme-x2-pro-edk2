from pathlib import Path
import json,re,hashlib,tarfile,gzip,struct,runpy
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel102')
ns={};exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
with tarfile.open(out/'stock-audio-contract.tar') as tf:
    members={m.name.removeprefix('k102-stock-audio-contract/'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in members['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(members[name.removeprefix('./')]).hexdigest()==digest
blob=gzip.decompress(members['stock-dtbo.img.gz']);assert hashlib.sha256(blob).hexdigest()==members['dtbo-before.sha'].decode().split()[0]
size,start,*_=struct.unpack_from('>8I',blob,struct.unpack_from('>8I',blob)[5])
overlay=blob[start:start+size]
assert overlay==(out/'stock-audio-extracted/overlay-0.dtbo').read_bytes()
nodes=ns['fdt_nodes'](overlay);records=[]
handles={struct.unpack('>I',p['phandle'])[0]:path for path,p in nodes.items() if 'phandle' in p}
symbols={name:value.decode().strip('\0') for name,value in nodes.get('/__symbols__',{}).items()}
fixups={}
for name,value in nodes.get('/__fixups__',{}).items():
    for location in value.decode().strip('\0').split('\0'):fixups[location]=name
def resolve(path,key,value):
    number=struct.unpack('>I',value[:4])[0]
    target=handles.get(number)
    names=[name for name,dest in symbols.items() if dest==target]
    return dict(local_target=target,local_symbols=names,external_symbol=fixups.get(path+':'+key+':0'),unresolved=target is None and path+':'+key+':0' not in fixups)
for path,p in nodes.items():
    if 'pm8008' not in path or path.startswith('/__'):continue
    keep={}
    for name,value in p.items():
        if name=='compatible':keep[name]=value.decode().strip('\0').split('\0')
        elif name=='reg':
            assert len(value)%2==0
            width=4 if len(value)%4==0 else 2
            keep[name]=dict(cell_bits=width*8,values=list(struct.unpack('>'+str(len(value)//width)+('I' if width==4 else 'H'),value)))
        elif name=='qcom,pm8008-reset-gpio':keep[name]=dict(gpio=struct.unpack('>3I',value)[1],flags=struct.unpack('>3I',value)[2],controller=resolve(path,name,value))
        elif name.endswith('-supply'):keep[name]=resolve(path,name,value)
        elif name=='interrupt-parent':keep[name]=resolve(path,name,value)
        elif name=='interrupts':keep[name]=list(struct.unpack('>'+str(len(value)//4)+'I',value))
        elif name=='interrupt-controller':keep[name]='present'
    if keep:records.append(dict(path=path,properties=keep))
report=dict(stock_archive_member_hashes_pass=True,stock_dtbo_hash_pass=True,mtp_overlay0_hash_pass=True,pm8008_nodes=records,stock_overlay_no_pm8008_interrupt_properties=not any('interrupts' in r['properties'] for r in records),sensor_identity_not_inferred_from_slot=True,no_phone_changes=True)
report.update(stock_top_level_pmic_irq_absent=all('interrupts' not in r['properties'] for r in records if re.search(r'qcom,pm8008@[4589]$',r['path'])),stock_internal_gpio_irq_description_present=any('pinctrl@c000' in r['path'] and 'interrupts' in r['properties'] for r in records))
(root/'reference/kernel120/stock-camera-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
