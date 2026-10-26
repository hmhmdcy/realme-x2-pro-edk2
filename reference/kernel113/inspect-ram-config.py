from pathlib import Path
import hashlib,json,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
path=out/'ram-v7-tree-private.tar'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='3ae4e703e6f8b67ecd57f84f089472c3f98d97b8eb9d345c417c12e589f934f3'
with tarfile.open(path) as t:
    data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
with tarfile.open(out/'sensor-ram-v7.tar') as t:
    member=next(m for m in t if m.name.endswith('ram-tree-after.sha256'))
    expected=t.extractfile(member).read().decode()
for line in expected.splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
allowed={'bus_type','bus_instance','slave_config','min_bus_speed_khz','max_bus_speed_khz',
         'dri_irq_num','irq_num','irq_pull_type','irq_drive_strength','irq_trigger_type',
         'is_chip_pin','num_rail','rail_on_state','vddio_rail','vdd_rail','rigid_body_type'}
def walk(obj,found):
    if isinstance(obj,dict):
        for key,value in obj.items():
            if key in allowed: found[key]=value.get('data',value) if isinstance(value,dict) else value
            elif key=='name' and value in allowed: found[value]={k:v for k,v in obj.items() if k in ('data','str','flt','sint')}
            walk(value,found)
    elif isinstance(obj,list):
        for value in obj: walk(value,found)
properties={}
for name,value in data.items():
    if not name.endswith('_platform.config') or not any(s in name for s in ['lsm6','mmc','stk','alsps']): continue
    found={}; walk(json.loads(value),found); properties[Path(name).name]=found
report=dict(ram_files=len(data),ram_tree_matches_trial_hashes=True,selected_bus_power_properties=properties,
            oem_modem_type_matches=(data['oppoVersion/modemType'].strip()==b'4'),
            calibration_contents_excluded=True,sensors_accepted=False)
(out/'ram-v7-hardware-properties-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
