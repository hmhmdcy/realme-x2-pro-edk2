from pathlib import Path
import ast, json, math
import numpy as np

ref=Path(__file__).resolve().parent
module=ast.parse((ref/'analyze-acoustic.py').read_text())
function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='analyze_samples')
ns={'np':np,'math':math};exec(compile(ast.Module(body=[function],type_ignores=[]),'actual_analyze_samples','exec'),ns)
analyze=ns['analyze_samples']
metadata=dict(code=[1,1,0,1,0,0,1,1,1,0,1,0,1,0,0],leading_silence_seconds=.5)
case=dict(case='synthetic',speaker='synthetic',target_speaker_enabled=True,frequency=997,play_start_after_capture_seconds=.62)
rate=48000;t=np.arange(288000)/rate;rng=np.random.default_rng(170)
noise=rng.normal(0,11,len(t));rows=[]
for latency in [0,.08,.4]:
    start=1.12+latency;offset=t-start;slots=np.floor(offset/.2).astype(int)
    envelope=np.array(metadata['code'])[np.clip(slots,0,14)]*((slots>=0)&(slots<15))
    signal=noise+30*envelope*np.sin(2*np.pi*997*t)
    row,*_=analyze(signal,case,metadata)
    assert row['best_code_energy_correlation']>.95 and row['on_to_off_band_power_db']>20,row
    rows.append(row)
for label,data in [('noise-only',noise),('uncoded-carrier',noise+30*np.sin(2*np.pi*997*t))]:
    row,*_=analyze(data,case,metadata)
    assert row['best_code_energy_correlation']<.4 and row['on_to_off_band_power_db']<6,row
    row['synthetic_case']=label;rows.append(row)
report=dict(stage=170,actual_analysis_function_tested=True,synthetic_positive_cases=3,
            noise_and_uncoded_tone_negative_controls_rejected=True,hardware_not_tested_by_synthetic_cases=True,results=rows)
(ref/'detector-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='results'}))
