from pathlib import Path
import json,struct
root=Path('/mnt/e/RealmeX2Pro edk2')
script=(root/'reference/kernel120/inspect-stock-camera-contract.py').read_text()
prefix=script.split('\nfor path,p in nodes.items():')[0]
env={};exec(compile(prefix,'stage120-stock-readonly-prefix','exec'),env)
nodes=env['nodes'];records=[]
for path,props in nodes.items():
 if 'qcom,cam-sensor@' not in path or path.startswith('/__'):continue
 result=dict(path=path,properties={})
 for key,value in props.items():
  if key in ['cell-index','cci-device','cci-master','csiphy-sd-index','gpio-reset','gpio-custom1','gpio-custom2','gpio-req-tbl-num','gpio-req-tbl-flags','rgltr-min-voltage','rgltr-max-voltage','clock-rates']:
   result['properties'][key]=list(struct.unpack('>'+str(len(value)//4)+'I',value))
  elif key in ['regulator-names','gpio-req-tbl-label','pinctrl-names','status']:result['properties'][key]=value.rstrip(b'\0').decode().split('\0')
  elif key.endswith('-supply'):result['properties'][key]=env['resolve'](path,key,value)
  elif key=='gpios':
   assert len(value)%12==0;gpio=[]
   for off in range(0,len(value),12):
    handle,number,flags=struct.unpack_from('>III',value,off);target=env['handles'].get(handle)
    symbols=[name for name,dest in env['symbols'].items() if dest==target]
    external=env['fixups'].get(path+':gpios:'+str(off))
    gpio.append(dict(number=number,flags=flags,local_symbols=symbols,external_symbol=external,unresolved=target is None and external is None))
   result['properties'][key]=gpio
 records.append(result)
assert len(records)==5
report=dict(stage=192,stock_dtbo_and_archive_hashes_verified=True,source='same-handset stock DTBO overlay0',slots=records)
(root/'reference/kernel192/stock-camera-slots-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for record in records:
 p=record['properties'];print(json.dumps(dict(slot=p.get('cell-index'),cci_device=p.get('cci-device'),cci_master=p.get('cci-master'),gpios=p.get('gpios'),custom1=p.get('gpio-custom1'),custom2=p.get('gpio-custom2'),supplies={k:v['local_symbols'] for k,v in p.items() if k.endswith('-supply')})))
