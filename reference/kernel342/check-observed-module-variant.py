"""Bind the retained descriptor variant to the observed main-camera actuator."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code='''
from pathlib import Path
import json,struct
base=Path('/sys/bus/i2c/drivers/s5kgw1');devices=[p for p in base.iterdir() if (p/'of_node/lens-focus').is_file()]
assert len(devices)==1
sensor=devices[0];phandle=(sensor/'of_node/lens-focus').read_bytes();assert len(phandle)==4
lenses=[]
for p in Path('/sys/bus/i2c/devices').iterdir():
 node=p/'of_node'
 if (node/'phandle').is_file() and (node/'phandle').read_bytes()==phandle:
  lenses.append(dict(driver=(p/'driver').resolve().name,name=(p/'name').read_text().strip(),address7=int(p.name.rsplit('-',1)[1],16),compatible=(node/'compatible').read_bytes().rstrip(b'\\0').decode()))
assert len(lenses)==1
print(json.dumps(dict(model='s5kgw1',lens=lenses[0])))
'''
actual=json.loads(host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
variants=json.loads((HERE.parent/'kernel274/actuator-contract-validation.json').read_text())['variants'];current={r['module']:r['sha256'] for r in json.loads((HERE.parent/'kernel326/descriptor-source-validation.json').read_text())['sources']}
for variant in variants:assert current[variant['variant']+'_s5kgw1']==variant['source_sha256']
assert actual['lens']['address7']==0x72 and actual['lens']['driver']=='lc898219xi' and actual['lens']['compatible']=='onnn,lc898219xi',actual
selected=[v for v in variants if v['address7']==actual['lens']['address7'] and v['name'].endswith(actual['lens']['driver'])];assert len(selected)==1
optical=json.loads((HERE.parent/'kernel274/focus-optical-analysis.json').read_text());assert optical
report=dict(stage=342,observed=actual,matching_retained_factory_variant=selected[0]['variant']+'_s5kgw1',factory_descriptor_hashes_match_current_inventory=True,
 binding_basis=['current sensor lens-focus phandle selects LC898219XI at0x72','274 physical optical response to that actuator protocol','274 independent descriptor/XML contract distinguishes Sunny LC898219XI from Qtech BU64253 at0x0c'],
 optical_evidence='../kernel274/focus-optical-analysis.json',actuator_evidence='../kernel274/actuator-contract-validation.json',
 manufacturer_eeprom_id_verified=False,absence_of_other_i2c_devices_probed=False,conditional_on_retained_factory_variant_inventory=True,mode_specific_aec_table_binding_verified=False,default_tuning_changed=False,passed=True)
(HERE/'module-variant-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
