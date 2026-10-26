from pathlib import Path
import json,sys
sys.path.insert(0,'/var/lib/samurai/k208-loc-tools')
from pqwm1 import decode
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes()
source=root/'k208-mm-debug-observer/mm-nmea-private.jsonl'
out=root/'k208-debug-analysis';out.mkdir(mode=0o700)
seen=set();records=[];errors=0
for line in source.read_text().splitlines():
    values=json.loads(line)
    for text in str(values.get('4','')).replace('\r','').split('\n'):
        if not text.startswith('$PQWM1,') or text in seen:continue
        seen.add(text)
        try:records.append(decode(text))
        except ValueError:errors+=1
(out/'pqwm1-records-private.json').write_text(json.dumps(records,indent=2)+'\n')
assert records
names=['time_valid','time_source','time_unc','clock_bias','clock_bias_unc','xo_state','pga_gain','gps_bp_i','gps_bp_q','adc_i','adc_q','jammer_gps','jammer_glo','jammer_bds','jammer_gal','error_recovery','agc_gps','agc_glo','agc_bds','agc_gal','leap_seconds','leap_unc','time_unc_ns']
ranges={name:dict(min=min(values),max=max(values),samples=len(values)) for name in names if (values:=[record[name] for record in records if record[name] is not None])}
report=dict(stage=208,source='MM GetLocation during existing debug-enabled session',pqwm1_distinct=len(records),checksum_or_parse_errors=errors,rf_clock_ranges=ranges,missing_field_samples={name:sum(record[name] is None for record in records) for name in names})
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
