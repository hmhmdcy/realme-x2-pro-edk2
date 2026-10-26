from pathlib import Path
import hashlib,json,re,struct
from gw1_data import Description
import host
R=Path(__file__).resolve().parent
d=Description('sunny');w=d.words(d.uid('sensorDriverData'))
selected=[]
for i in [w[45],w[49],w[51],w[54],w[56]]:
 x=d.entries[i];b=d.payload(i);selected.append(dict(id=i,name=x['name'],size=len(b),hex=b.hex()))
settings={}
for name,off in [('stream_on',57),('stream_off',59),('group_on',61),('group_off',63)]:
 settings[name]=d.regs(w[off+1],w[off])
log=Path('/mnt/e/edk2-samurai-out/kernel250/android-gnss-r2-root-private/dmesg-after.txt')
lines=log.read_text(errors='replace').splitlines()
probe=[l for l in lines if 'Probe success,slot:0,slave_addr:0x20,sensor_id:0x971' in l];assert len(probe)==1
direct={v:json.loads((host.PRIVATE.parent/'kernel270'/('gw1-'+v+'-direct-registers-private.json')).read_text()) for v in ['qtech','sunny']}
assert direct['qtech']['init']==direct['sunny']['init']
assert len(direct['qtech']['modes'])==len(direct['sunny']['modes'])==10
assert direct['qtech']['modes']==direct['sunny']['modes']
report=dict(stage=272,stock_probe_source_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),stock_probe_slot=0,stock_probe_address8=32,
 main_address7=16,chip_id=2417,address_matches_sunny_description=True,module_vendor_not_proven_from_address_alone=True,
 both_module_initialization_and_mode_tables_equal=True,
 control_registers=dict(frame_length=w[18],line_length=w[19],exposure=w[20],analogue_gain=w[23]),
 global_max_analogue_gain=struct.unpack('<d',struct.pack('<Q',w[42]))[0],exposure_margin=w[46],selected=selected,settings=settings,
 no_hardware_operation=True)
(R/'control-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
