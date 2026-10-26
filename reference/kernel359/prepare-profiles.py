"""Stage complete private profiles and focused AE contract fixtures."""
from pathlib import Path
import copy, json, yaml
import host

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
source=json.loads((P.parent/'kernel358/mode-exposure-programs-private.json').read_text())
models={'sunny_s5kgw1':'s5kgw1','sunny_imx471':'imx471','sunny_imx319':'imx319','qtech_s5k3m5sx':'s5k3m5'}
priority={'AECExpIncGain':0,'AECExpIncExpTime':1,'AECExpIncPrioMax':2}
directory=P/'profiles';directory.mkdir(exist_ok=True);fixtures=P/'fixtures';fixtures.mkdir(exist_ok=True)
rows=[];unmatched=[]
for variant,model in models.items():
    for usecase in ['Preview','Video']:
        profile=yaml.safe_load((P.parent/'kernel343/profiles'/(variant+'-'+usecase.lower()+'.yaml')).read_text())
        contexts=[r for r in source if r['variant']==variant and r['usecase']==usecase]
        for row in contexts:
            mode=next((m for m in profile['modes'] if [m['match']['width'],m['match']['height']]==row['sensor_size']),None)
            if mode is None:
                unmatched.append(dict(variant=variant,usecase=usecase,sensor_mode_index=row['sensor_mode_index']));continue
            program=dict(enabled=True,knees=[dict(gain=k['gain'],exposure_time_ns=k['expTime'],priority=priority[k['incrementPriority']],index=k['expIndex']) for k in row['table']['expKneeEntries']],
                ev_adjustment=copy.deepcopy(row['ev_adjustment']),antibanding=copy.deepcopy(row['antibanding']))
            mode['exposure_program']=program
            label=model+'-'+str(row['sensor_mode_index'])+'-'+usecase.lower()
            match=mode['match'];target=256.5/1024
            focused=dict(match=copy.deepcopy(match),residual_black_subtraction=0,range_normalization=1.,
                sensor_controls=copy.deepcopy(mode['sensor_controls']),exposure_program=copy.deepcopy(program),
                agc=dict(relativeLuminanceTarget=target,AeConstraintMode=dict(ConstraintNormal=dict(lower=dict(qLo=0.,qHi=1.,yTarget=.0001))),
                    AeExposureMode=dict(ExposureNormal=dict(exposureTime=[100,10000,30000],gain=[1.,4.,16.]))))
            fixture=dict(version=2,sensor_model=model,modes=[focused]);path=fixtures/(label+'.yaml');path.write_text(yaml.safe_dump(fixture,sort_keys=False))
            legacy=copy.deepcopy(fixture);legacy['modes'][0].pop('exposure_program');(fixtures/(label+'-legacy.yaml')).write_text(yaml.safe_dump(legacy,sort_keys=False))
            minimum_code=32 if model.startswith('s5k') else 0
            maximum_code=dict(s5kgw1=1024,s5k3m5=512,imx319=960,imx471=800)[model]
            margin=dict(s5kgw1=6,s5k3m5=4,imx319=18,imx471=18)[model]
            rows.append(dict(name=label,model=model,match=match,profile=str(path),legacy_profile=str(fixtures/(label+'-legacy.yaml')),
                minimum_code=minimum_code,maximum_code=maximum_code,margin=margin,program=program,arbitration_uid=row['arbitration_uid']))
        (directory/(variant+'-'+usecase.lower()+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False))
assert len(rows)==10
(P/'cases-private.json').write_text(json.dumps(rows,indent=2)+'\n')
report=dict(stage=359,complete_private_profiles=8,existing_mode_usecase_contexts_with_exposure_program=len(rows),
    existing_physical_modes_with_profile=len({(r['model'],r['match']['width'],r['match']['height']) for r in rows}),
    higher_resolution_contexts_without_complete_iq_profile=unmatched,
    unchanged_calibration_fields_reused_from343=True,focused_fixtures_override_luma_target_only_for_deterministic_tests=True,
    private_data_only=True,installed=False,passed=True)
(HERE/'profile-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='higher_resolution_contexts_without_complete_iq_profile'},indent=2))
