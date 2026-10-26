"""Summarize verified private RF/clock snapshots without exporting NMEA or IDs."""
from pathlib import Path
import collections,importlib.util,json,re,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel242/clock-evidence')
sys.path.insert(0,str(R.parent/'kernel226'))
from loc_decode import summarize,nmea_text
spec=importlib.util.spec_from_file_location('pqwm',R.parent/'kernel208/pqwm1.py')
pqwm=importlib.util.module_from_spec(spec);spec.loader.exec_module(pqwm);assert pqwm.selftest()['missing_and_nan_not_zero']
rows=[json.loads(line) for line in (P/'events-private.jsonl').read_text().splitlines()]
summary=summarize(rows)
trace=(P/'trace-private.txt').read_text()
events=collections.Counter(re.findall(r'\b((?:clk|regulator)_[a-z0-9_]+):',trace))
names=['xo_board','bi_tcxo','bi_tcxo_ao','rf_clk1','rf_clk1_ao','rf_clk2','rf_clk2_ao','rf_clk3','rf_clk3_ao']
snapshots={}
for label in ['before','active-5','active-30','active-75','after']:
 snap=json.loads((P/(label+'-private.json')).read_text());clocks={}
 for line in snap['clk'].splitlines():
  fields=line.split()
  if len(fields)>9 and fields[0] in names:
   assert fields[8] in ['Y','N','?']
   clocks[fields[0]]=dict(enable=int(fields[1]),prepare=int(fields[2]),protect=int(fields[3]),nominal_rate=int(fields[4]),debugfs_display=fields[8])
 snapshots[label]=clocks
rf=[];decode_errors=0
for row in rows:
 if row['kind']!='indication' or row['message_id']!=0x26:continue
 raw=bytes.fromhex(row['tlvs'].get('16') or row['tlvs'].get('1') or '')
 if not raw:continue
 for text in nmea_text(raw).replace('\r','').split('\n'):
  if not text.startswith('$PQWM1,'):continue
  try:rf.append(pqwm.decode(text))
  except ValueError:decode_errors+=1
rf_summary={}
for name in ['time_valid','time_source','time_unc','time_unc_ns','clock_bias','clock_bias_unc','xo_state','pga_gain','adc_i','adc_q','jammer_gps','jammer_glo','jammer_bds','jammer_gal','error_recovery','agc_gps','agc_glo','agc_bds','agc_gal']:
 values=[x[name] for x in rf if x[name] is not None]
 rf_summary[name]=dict(samples=len(values),min=min(values) if values else None,max=max(values) if values else None)
assert not decode_errors
gpio_before=json.loads((P/'before-private.json').read_text())['gpio']
gpio_after=json.loads((P/'after-private.json').read_text())['gpio']
report=dict(stage=242,receiver=summary,trace_event_counts=dict(events),
 relevant_clock_trace_events=sum(v for k,v in events.items() if k.startswith('clk_')),
 regulator_trace_events=sum(v for k,v in events.items() if k.startswith('regulator_')),
 rpmh_clock_snapshots=snapshots,gpio_text_before_after_equal=gpio_before==gpio_after,
 pqwm1_reports=len(rf),pqwm1_decode_errors=decode_errors,rf_clock_numeric_ranges=rf_summary,
 adc_agc_changes_not_hardware_or_antenna_proof=True,xo_state_enum_not_claimed_locked=True,
 no_rf_clock_enablement_or_lock_inferred_from_debugfs=True,
 no_ap_transition_does_not_prove_no_modem_rf_votes=True,android_runtime_capture=False)
(R/'clock-analysis-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=242,valid_snr=summary['sv']['valid_snr'],positive_snr=summary['sv']['positive_snr'],valid_track=summary['sv']['valid_track'],missing_lists=summary['sv']['reports_without_either_list'],clock_trace_events=report['relevant_clock_trace_events'],regulator_trace_events=report['regulator_trace_events'],pqwm1_reports=len(rf),rf_clock_numeric_ranges=rf_summary)))
