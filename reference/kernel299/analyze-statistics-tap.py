"""Record the observed BLS/WB influence on statistics for future hardware AE."""
from pathlib import Path
import json,statistics
HERE=Path(__file__).resolve().parent
d=json.loads((HERE/'factory-bls-capture-validation.json').read_text());assert d['passed']
rows=[]
for phase in range(6):
 s=[r for r in d['statistics'] if r['phase']==phase and r['frame']%9>=4]
 rows.append(dict(phase=phase,population=sorted(set(r['sum'] for r in s)),weighted_sums=sorted(set(r['weighted'] for r in s)),mean_bin=statistics.mean(r['weighted']/r['sum'] for r in s)))
assert all(r['population']==[820560] for r in rows)
assert rows[1]['weighted_sums']==rows[2]['weighted_sums']==rows[3]['weighted_sums']
assert rows[0]['weighted_sums']==rows[4]['weighted_sums']
assert rows[5]['mean_bin']<rows[1]['mean_bin']<rows[0]['mean_bin']
report=dict(stage=299,kernel_build=298,physical_sensor_pattern=True,roi_unchanged=True,phases=rows,
 histogram_changes_with_bls=True,wb_gain_changes_leave_histogram_exactly_unchanged=True,
 inference='Observed statistics tap follows BLS and precedes WB in this configuration; gamma/CST output brightness is a different domain',
 ae_must_not_treat_gamma_encoded_output_as_linear_statistics=True,rgb_awb_statistics_not_provided=True,
 severe_irq_delay_and_multi_request_acceptance_still_pending=True)
(HERE/'statistics-tap-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
