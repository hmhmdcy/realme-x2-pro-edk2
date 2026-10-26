"""Use the prior strict decoders; missing fields are never counted as zero."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parent
s=(R.parent/'kernel242/analyze-clock-session.py').read_text().replace('/kernel242/clock-evidence','/kernel243/evidence/k243-window-clock').replace('stage=242','stage=243').replace('clock-analysis-validation.json','window-analysis-validation.json')
exec(compile(s,str(R/'analyze-window.py'),'exec'))
report=json.loads((R/'window-analysis-validation.json').read_text())
root=Path('/mnt/e/edk2-samurai-out/kernel243/evidence/k243-window-clock');logs={}
for name in ['tftp','rmtfs']:
 a=(root/('before-'+name+'-private.log')).read_bytes();b=(root/('after-'+name+'-private.log')).read_bytes()
 delta=b[len(a):] if b.startswith(a) else None
 logs[name]=dict(before_bytes=len(a),after_bytes=len(b),append_only=b.startswith(a),new_bytes=len(delta) if delta is not None else None,new_lines=len(delta.splitlines()) if delta is not None else None,
  new_error_keyword_lines=sum(bool(re.search(rb'error|failed|not found',x,re.I)) for x in delta.splitlines()) if delta is not None else None,
  namespace_delete_only=bool(delta) and all(b'del_client' in line or line.startswith(b'[RMTFS] packet; from:') for line in delta.splitlines()),
  full_log_private=True)
genpd={}
for label in ['before','active-5','active-30','active-75','after']:
 text=json.loads((root/(label+'-private.json')).read_text())['genpd']
 genpd[label]=[line.strip() for line in text.splitlines() if re.search(r'^(?:\s*)(?:mss|modem|cx|mx|mxc|lmx|lcx)(?:\s|$)',line)]
report.update(environment='indoor window opened; other phones receive GPS per user',file_services=logs,relevant_genpd_rows=genpd,genpd_state_not_physical_clock_or_lna_measurement=True)
previous=json.loads((R.parent/'kernel242/clock-analysis-validation.json').read_text())
report['previous242_rf_comparison']={k:dict(previous=previous['rf_clock_numeric_ranges'][k],current=report['rf_clock_numeric_ranges'][k]) for k in ['pga_gain','agc_gps','jammer_gps','jammer_glo','jammer_bds','jammer_gal']}
report['gain_and_jammer_changes_not_calibrated_interference_or_lna_diagnosis']=True
(R/'window-analysis-validation.json').write_text(json.dumps(report,indent=2)+'\n')
health=json.loads((root/'summary.json').read_text());(R/'window-session-validation.json').write_text(json.dumps(health,indent=2)+'\n')
print(json.dumps(dict(stage=243,valid_snr=report['receiver']['sv']['valid_snr'],positive_snr=report['receiver']['sv']['positive_snr'],valid_track=report['receiver']['sv']['valid_track'],file_services=logs,relevant_genpd_rows=genpd)))
