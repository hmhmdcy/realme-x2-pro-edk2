"""Compare independently decoded PQWM1 and opaque RF words; label inference."""
from pathlib import Path
import collections,importlib.util,json,struct,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel246');sys.path.insert(0,str(R.parent/'kernel226'));from loc_decode import nmea_text
spec=importlib.util.spec_from_file_location('pqwm246',R.parent/'kernel208/pqwm1.py');pqwm=importlib.util.module_from_spec(spec);spec.loader.exec_module(pqwm);assert pqwm.selftest()['missing_and_nan_not_zero']
decoded={};rf={};clock={};spectrum={};report=dict(stage=246,phases={},wire_fields_not_named_without_definition=True,comparisons_are_two_sequential_sessions_not_aba=True)
for label in ['baseline-off','comparison-online']:
 o=P/(label+'-snapshot');rows=[json.loads(x) for x in (o/(label+'-loc-events-private.jsonl')).read_text().splitlines()];nmea=[]
 for row in rows:
  if row['kind']!='indication' or row['message_id']!=0x26:continue
  raw=bytes.fromhex(row['tlvs'].get('16') or row['tlvs'].get('1') or '')
  if not raw:continue
  for text in nmea_text(raw).replace('\r','').split('\n'):
   if text.startswith('$PQWM1,'):nmea.append(dict(elapsed_us=row['elapsed_us'],**pqwm.decode(text)))
 logs=json.loads((P/(label+'-decoded-log-envelopes-private.json')).read_text());rf[label]=[bytes.fromhex(x['payload_hex'])[16:] for x in logs if x['code']==0x147e];clock[label]=[bytes.fromhex(x['payload_hex'])[16:] for x in logs if x['code']==0x1478];ss=[bytes.fromhex(x['payload_hex'])[16:] for x in logs if x['code']==0x1635];assert len(nmea)==90 and all(len(b)==722 and b[0]==5 for b in rf[label]) and all(len(b)==174 and b[0]==3 for b in clock[label])
 ranges={k:dict(samples=len(v),min=min(v) if v else None,max=max(v) if v else None) for k in ['time_valid','time_source','time_unc_ns','clock_bias','clock_bias_unc','xo_state','pga_gain','adc_i','adc_q','jammer_gps','jammer_glo','jammer_bds','jammer_gal','error_recovery','agc_gps','agc_glo','agc_bds','agc_gal'] for v in [[x[k] for x in nmea if x[k] is not None]]}
 # Structural inference only: 331 = 6 + 13*25. In each packet, all13 candidate
 # word1-word0 differences share a base integer. The initial single-base GPS
 # assumption was rejected; three different packet bases actually occur.
 # This validates arithmetic, not proprietary field names, units or flags.
 spectra=[]
 for b in ss:
  assert len(b)==331 and b[0]==2;slots=[]
  for i in range(13):
   delta,freq,w0,w1,w2,w3,flag=struct.unpack_from('<iIIIIIB',b,6+i*25);slots.append(dict(delta_integer=delta,frequency_integer=freq,raw_words=[w0,w1,w2,w3],raw_flag=flag))
  assert len({v['frequency_integer']-v['delta_integer'] for v in slots})==1
  spectra.append(slots)
 used=[v for row in spectra for v in row if any(v['raw_words'])];spectrum[label]=spectra;decoded[label]=nmea
 centers=collections.Counter(row[0]['frequency_integer']-row[0]['delta_integer'] for row in spectra)
 report['phases'][label]=dict(pqwm1_reports=len(nmea),pqwm1_ranges=ranges,prx_hw_reports=len(rf[label]),clock_reports=len(clock[label]),spectrum_reports=len(ss),inferred_spectrum_13_slots_arithmetic_relation_all_pass=True,spectrum_base_integer_counts=dict(centers),nonzero_word_slots_counts=dict(collections.Counter(sum(any(v['raw_words']) for v in row) for row in spectra)),nonzero_slot_delta_integer_range=dict(min=min(v['delta_integer'] for v in used),max=max(v['delta_integer'] for v in used)),spectrum_units_flags_power_and_interference_threshold_not_claimed=True)
for name,data in [('prx_hw',rf),('clock',clock)]:
 a=data['baseline-off'];b=data['comparison-online'];size=len(a[0]);stable_changes=[]
 for i in range(size):
  aa={x[i] for x in a};bb={x[i] for x in b}
  if len(aa)==len(bb)==1 and aa!=bb:stable_changes.append(i)
 report[name+'_constant_byte_changes']=stable_changes
# An empirical association with the independently parsed ADC values can guide
# future layout work. It does not prove register names or electrical health.
candidates={}
for field in ['adc_i','adc_q']:
 hits=[]
 for offset in range(719):
  phases=[]
  for label in ['baseline-off','comparison-online']:
   values=[x[field] for x in decoded[label]];words=[struct.unpack_from('<i',b,offset)[0] for b in rf[label]];best=(0,0,0)
   for shift in range(-3,4):
    pairs=[(values[i],words[i+shift]) for i in range(len(values)) if 0<=i+shift<len(words) and values[i] is not None];matches=sum(a==b for a,b in pairs)
    if matches>best[0]:best=(matches,len(pairs),shift)
   phases.append(dict(matches=best[0],compared=best[1],lag=best[2]))
  if all(x['matches']>=80 for x in phases):hits.append(dict(byte_offset=offset,phase_matching=phases))
 candidates[field]=hits
report['empirical_prx_adc_word_candidates']=candidates;report['empirical_association_is_not_documented_wire_schema']=True
(P/'rf-comparison-decoded-private.json').write_text(json.dumps(dict(pqwm1=decoded,spectra=spectrum),indent=2)+'\n');(R/'rf-comparison-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
