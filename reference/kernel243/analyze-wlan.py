from pathlib import Path
import json
R=Path(__file__).resolve().parent
s=(R.parent/'kernel242/analyze-clock-session.py').read_text().replace('/kernel242/clock-evidence','/kernel243/wlan-evidence/k243-wlan-off-clock').replace('stage=242','stage=243').replace('clock-analysis-validation.json','wlan-analysis-validation.json')
exec(compile(s,str(R/'analyze-wlan.py'),'exec'))
report=json.loads((R/'wlan-analysis-validation.json').read_text());baseline=json.loads((R/'window-analysis-validation.json').read_text())
report.update(environment='same opened window; WLAN softblocked only; USB capture',comparison={k:dict(wlan_on=baseline['rf_clock_numeric_ranges'][k],wlan_off=report['rf_clock_numeric_ranges'][k]) for k in ['pga_gain','agc_gps','jammer_gps','jammer_glo','jammer_bds','jammer_gal']})
(R/'wlan-analysis-validation.json').write_text(json.dumps(report,indent=2)+'\n')
root=Path('/mnt/e/edk2-samurai-out/kernel243/wlan-evidence')
for folder,target in [('k243-wlan-control','wlan-control-validation.json'),('k243-wlan-off-clock','wlan-session-validation.json')]:
 v=json.loads((root/folder/'summary.json').read_text());(R/target).write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(dict(stage=243,valid_snr=report['receiver']['sv']['valid_snr'],positive_snr=report['receiver']['sv']['positive_snr'],valid_track=report['receiver']['sv']['valid_track'],comparison=report['comparison'])))
