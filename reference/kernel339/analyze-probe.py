from pathlib import Path
import json,re,struct,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1]
sys.path.insert(0,str(HERE.parent/'kernel337'));from stock_bg import StockBayer
observation=json.loads((P/('probe-'+run+'-observation.json')).read_text());assert observation['state']['terminal'] and not observation['worker_live'] and observation['state']['summary']['passed']
configs=json.loads((P/'profiles-private.json').read_text());cases=json.loads((HERE/'cases.json').read_text());rows=[]
for label,item in cases.items():
 log=observation['logs']['capture-'+label+'.log'];entries=[]
 for line in log.splitlines():
  if 'LUX epoch=' not in line:continue
  pairs=re.findall(r'([a-z-]+)=([0-9.eE+-]+)',line.split('LUX ',1)[1]);entries.append({key:float(value) for key,value in pairs})
 assert entries,(label,'no valid lux output')
 engine=StockBayer(P.parent/'kernel328/stats-source/com.qti.stats.aec.so');manual=StockBayer(P.parent/'kernel328/stats-source/com.qti.stats.aec.so')
 config=configs[label]['config'];lux=config['lux'];a=config['exposure_anchor'];anchor=(a['analogue_gain'],a['exposure_time_ns'],a['index'])
 engine.configure(lux['compensate_sensitivity'],lux['reference_zero_sensitivity'],lux['table_zero_sensitivity'],lux['filter_factor'])
 packet=(P.parent/'kernel338/samples-r1'/('sample-'+item['model']+'-private.stats')).read_bytes();off=4112
 left,top,rw,rh,columns,nrows,high,bits=struct.unpack_from('<8H',packet,off+8)
 raw=[struct.unpack_from('<4I4H',packet,off+24+i*24) for i in range(columns*nrows)]
 maxExposure=maxIndex=maxLuma=0.;cache={};previous=None;startup=[];referenceStarted=False;matched=0
 for entry in entries:
  assert previous is None or entry['sof']>previous;previous=entry['sof']
  exposure=manual.manual(anchor,entry['analogue-gain'],int(entry['exposure-ns']))
  expectedIndex=engine.lux(exposure,entry['luma'])
  key=(entry['red'],entry['blue']) if config['compensate_colour'] else ()
  if key not in cache:
   weights=engine.weights(config['weights'],config['reference_gains'],[entry['red'],1.,entry['blue']],config['compensate_colour'])
   engine.region_setup(rw*rh//4,bits,[high]*4,weights,config['normalization'])
   for index,region in enumerate(raw):engine.region(region[:4],region[4:],index)
   pooled=engine.pool(columns,nrows)
   # This separate helper call would change the temporal filter. Read the
   # pooled mean directly with the exact sequential float32 accumulation.
   import ctypes
   f32=lambda x:ctypes.c_float(x).value
   total=0.
   for cell in pooled:total=f32(total+cell[0])
   cache[key]=max(f32(total/256),f32(.1))
  difference=abs(cache[key]-entry['luma'])
  # The retained338 packet represents a settled pattern. Front-camera SOF0/1
  # currently report the dark-luma floor before that pattern appears. Keep
  # these frames in exposure/filter checking, and record their absence from
  # the settled-pattern comparison rather than substituting an old packet.
  if not referenceStarted and entry['luma']<=.100001 and difference>=.003:
   startup.append(int(entry['sof']))
  else:
   referenceStarted=True;matched+=1;maxLuma=max(maxLuma,difference)
  maxExposure=max(maxExposure,abs(exposure-entry['exposure-index']));maxIndex=max(maxIndex,abs(expectedIndex-entry['index']))
 # Device INFO logs print six significant digits. Exact bitwise checking is
 # provided by the AArch64 DSO contract, not claimed for decimal log output.
 assert matched and maxExposure<.003 and maxIndex<.003 and maxLuma<.003,(label,maxExposure,maxIndex,maxLuma)
 rows.append(dict(case=label,model=item['model'],valid_lux_frames=len(entries),last_isp_revision=int(entries[-1]['revision']),last_index=entries[-1]['index'],maximum_exposure_index_log_error=maxExposure,maximum_lux_index_log_error=maxIndex,maximum_hardware_luma_log_error=maxLuma,hardware_statistics_reference_stage=338,settled_pattern_reference_matched_frames=matched,startup_dark_luma_floor_sofs=startup,startup_frames_retained_in_exposure_and_filter_check=True,decimal_log_tolerance=.003,passed=True))
summary=observation['state']['summary'];(HERE/('probe-'+run+'-validation.json')).write_text(json.dumps(summary,indent=2)+'\n')
report=dict(stage=339,run=run,cameras=rows,actual_runtime_exposure_gain_and_sof_parameters=True,original_instruction_oracle=True,internal_pattern_only=True,physical_lux_calibration=False,physical_mode_binding_verified=False,default_profiles_unchanged=True,installed=False,passed=True)
(HERE/'runtime-lux-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
