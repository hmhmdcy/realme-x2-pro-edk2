from pathlib import Path
import hashlib,json

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
source=Path('/mnt/e/edk2-samurai-out/kernel111/source-files/k111-sensor-sources-readonly/sensors-vendor/config')
reference=out/'lineage18-sensor-configs-reference-private/config'
allowed={'bus_type','bus_instance','slave_config','min_bus_speed_khz','max_bus_speed_khz',
    'dri_irq_num','irq_num','irq_pull_type','irq_drive_strength','irq_trigger_type',
    'is_chip_pin','num_rail','rail_on_state','vddio_rail','vdd_rail','rigid_body_type',
    'soc_id','hw_platform','hw_platform_subtype','platform_version','modemType','prjName'}

def walk(obj,path,found):
    if isinstance(obj,dict):
        for key,value in obj.items():
            nested=path+'/'+key
            if key in allowed:
                found[nested]=value
            walk(value,nested,found)
    elif isinstance(obj,list):
        for i,value in enumerate(obj): walk(value,path+'/'+str(i),found)

private={}; summaries=[]
for origin,root in (('original',source),('lineage18',reference)):
    for path in sorted(root.glob('*.json')):
        if not any(part in path.name for part in ('lsm6ds3c','mmc5603','stk3331','default_sensors')): continue
        payload=path.read_bytes()
        try: obj=json.loads(payload)
        except json.JSONDecodeError:
            summaries.append(dict(origin=origin,name=path.name,json_parseable=False))
            continue
        found={};walk(obj,'',found)
        private[origin+'/'+path.name]=found
        summaries.append(dict(origin=origin,name=path.name,sha256=hashlib.sha256(payload).hexdigest(),
            json_parseable=True,top_level_keys=sorted(obj),hardware_property_paths=sorted(found)))
(out/'config-reference-hardware-fields-private.json').write_text(json.dumps(private,indent=2)+'\n')
report=dict(configurations=summaries,hardware_fields_saved_privately=True,
    calibration_values_excluded=True,phone_configuration_changed=False,
    platform_selection_error_proven=False)
(ref/'config-reference-schema.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(configurations=len(summaries),parseable=sum(x['json_parseable'] for x in summaries),
    original_top_level_keys={x['name']:x.get('top_level_keys') for x in summaries if x['origin']=='original'},
    reference_top_level_keys={x['name']:x.get('top_level_keys') for x in summaries if x['origin']=='lineage18'})))
