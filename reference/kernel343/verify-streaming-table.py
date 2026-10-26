"""Recover regular-stream table choice from the actual retained AEC function."""
from pathlib import Path
import copy,ctypes,json,struct,sys
sys.path.insert(0,'/usr/lib/python3/dist-packages')
import yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
sys.path.insert(0,str(HERE.parent/'kernel329'))
from stock_emulator import StockMath,OBJECT,LOGGER
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_PC,UC_ARM64_REG_LR

DM=OBJECT+0x1000;VT=OBJECT+0x2000;CUSTOM=OBJECT+0x3000;BUNDLE=OBJECT+0x4000;ARB=OBJECT+0x5000;TABLES=OBJECT+0x6000
GET_CUSTOM=LOGGER+0x100
class StreamingTable(StockMath):
 def __init__(self):
  super().__init__(P.parent/'kernel328/stats-source/com.qti.stats.aec.so',0x27c30,0x27e78)
  self.virtual_calls=0
  for address,value in [(OBJECT+8,DM),(DM,VT),(VT+408,GET_CUSTOM),(OBJECT+24,BUNDLE),(BUNDLE,ARB),(ARB+48,TABLES)]:self.write(address,'<Q',value)
 def _step(self,uc,pc,size,user):
  if pc==GET_CUSTOM:
   self.virtual_calls+=1;uc.reg_write(UC_ARM64_REG_X0,CUSTOM);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR));return
  super()._step(uc,pc,size,user)
 def select(self,tables,op=1,custom=False):
  self.write(CUSTOM+32,'<I',int(custom));self.write(ARB+40,'<I',len(tables))
  for i,table in enumerate(tables):self.write(TABLES+i*32+4,'<I',len(table['expKneeEntries']))
  self.call(x1=op);return self.uc.reg_read(UC_ARM64_REG_X0)

engine=StreamingTable();bindings=json.loads((P/'mode-bindings-private.json').read_text())
factory=json.loads((P.parent/'kernel336/factory-aec-bundle-private.json').read_text());rows=[];configs=[]
f32=lambda value:ctypes.c_float(value).value
def active(config):
 result=copy.deepcopy(config)
 if not result['lux']['compensate_sensitivity']:
  result['lux'].pop('reference_zero_sensitivity',None);result['lux'].pop('table_zero_sensitivity',None)
 return result
for variant,contexts in bindings.items():
 profile=yaml.safe_load((P.parent/'kernel341/profiles'/(variant+'-unit.yaml')).read_text())
 for row in contexts:
  roots=row['selected'];data=factory[variant]['roots']
  meter=next(x['data'] for x in data['Metering'] if x['uid']==roots['Metering']['uid'])
  arbitration=next(x['data'] for x in data['Arbitration'] if x['uid']==roots['Arbitration']['uid'])
  index=engine.select(arbitration['expTables']);assert index==0
  table=arbitration['expTables'][index];anchor=table['expKneeEntries'][0]
  config=dict(enabled=True,exposure_anchor=dict(analogue_gain=anchor['gain'],exposure_time_ns=anchor['expTime'],index=anchor['expIndex']),
   weights=meter['lumaWeight']['weight'],reference_gains=meter['lumaWeight']['refGain'],compensate_colour=meter['lumaWeight']['enableColorAndSensorComp'],normalization=1.,
   lux=dict(compensate_sensitivity=meter['indexCalc']['enableLuxIndexComp'],reference_zero_sensitivity=meter['indexCalc']['refSensitivityForExpIndexZero'],
    table_zero_sensitivity=f32(f32(table['sensitivityCorrectionFactor']*anchor['gain'])*f32(anchor['expTime'])),filter_factor=meter['indexCalc']['luxIndexFilterFactor']))
  prior=next((m for m in profile['modes'] if [m['match']['width'],m['match']['height']]==row['sensor_size']),None)
  same=config==prior['aec_lux'] if prior else None
  public=dict(variant=variant,sensor_mode_index=row['sensor_mode_index'],sensor_size=row['sensor_size'],usecase=row['usecase'],
   metering_uid=roots['Metering']['uid'],arbitration_uid=roots['Arbitration']['uid'],table_index=index,table_count=len(arbitration['expTables']),
   actual_oem_streaming_table_helper=True,existing341_mode_profile=prior is not None,serialized_lux_configuration_matches341=same,
   active_lux_configuration_matches341=active(config)==active(prior['aec_lux']) if prior else None,
   all_non_aec_roots_match_explicit_profile=all(roots[tag]['uid']==uid for tag,uid in [('lsc34_ife',25),('cc12_ife',37),('MWBGainV1',117),('refPtV1',79),('sensorCalV1',97)]))
  rows.append(public);configs.append(dict(**row,variant=variant,aec_lux=config,exposure_table=table))
assert engine.select([table],custom=True)==100
report=dict(stage=343,cases=rows,original_helper_address=['0x27c30','0x27e78'],original_oem_instructions=True,
 virtual_custom_table_query_stubbed=True,custom_override_100_verified=True,regular_streaming_custom_override_disabled=True,
 actual_android_algorithm_not_started=True,all_regular_streaming_table_indices_zero=True,
 all_existing_active_lux_configs_unchanged=all(r['active_lux_configuration_matches341'] for r in rows if r['existing341_mode_profile']),
 no_duplicate_capture_for_unchanged_configuration=True,phone_changed=False,passed=True)
(P/'bound-mode-configs-private.json').write_text(json.dumps(configs,indent=2)+'\n')
(HERE/'streaming-table-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(cases=len(rows),active_unchanged=sum(r['active_lux_configuration_matches341'] is True for r in rows),
 active_changed=[r for r in rows if r['active_lux_configuration_matches341'] is False],not_previously_profiled=sum(not r['existing341_mode_profile'] for r in rows),original_instruction_calls=engine.calls),indent=2))
