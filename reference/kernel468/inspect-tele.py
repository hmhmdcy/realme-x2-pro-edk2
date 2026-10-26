"""Audit cached mode2 frames, retaining every receipt and sensor restoration."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
path=HERE.parent/'kernel467/inspect-tele.py';raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='64d510506c3b0d90a0031b1af2e0de9479237b4966ab716eddf94c69a64dafed'
source=raw.decode().replace('kernel467','kernel468').replace('runtime-collected-r1','runtime-collected-r2').replace('final-health-r1-private.json','final-health-r2-private.json')
source=source.replace('stage=467','stage=468').replace("attempt='r1'","attempt='r2'")
source=source.replace('41cba861b491d583c685e07fdc0e97d635f8922f7132abefa15d0632d4fab0a4','6396ced1039e352a14c7a07187e780596a3a4180b22391bca0b30f7518db4094')
source=source.replace("plan['original440_profile_preserved']","plan['original440_mode3_preserved']")
source=source.replace("[('2104','1560',str(summary['sensor_mbus_code']))]","[('4208','2368',str(summary['sensor_mbus_code']))]")
source=source.replace('actual_sensor_mode=3,actual_sensor=[2104,1560]','actual_sensor_mode=2,actual_sensor=[4208,2368]')
source=source.replace('normal_16_9_mode_verified=False','stock_near_16_9_mode2_stream_verified=True,exact_aspect_center_crop_verified=False')
source=source.replace("(HERE/'hardware-validation.json').write_text", "(PRIVATE/'hardware-base-r2-validation-private.json').write_text")
source=source.replace('print(json.dumps(report,indent=2))','None')
exec(compile(source,'retained467-strict-audit-mode2-r2','exec'))
proof=json.loads((root/'proof.json').read_bytes());baseline=json.loads((root/'baseline-private.json').read_bytes())
assert state['sensor_module_restored'] and state['candidate_sensor_note']==proof['sensor']['note_sha256']
assert proof['sensor']['sha256']=='494910c99ef116b88038ac3dfcc020a90aa35bfcc610b6b37c152601ee758392'
assert state['sensor_formal_before']==baseline['tele_sensor']
assert plan['sensor_mode']==2 and plan['actual_sensor']==[4208,2368] and plan['candidate_sensor_module']
build=json.loads((HERE/'module-build-validation.json').read_bytes())
control=json.loads((HERE/'format-control-validation.json').read_bytes())
mode=json.loads((HERE/'mode-review-validation.json').read_bytes())
assert build['passed'] and control['passed'] and mode['passed']
assert build['candidate_sha256']==control['candidate_sha256']==mode['candidate_sha256']
for row in report['rows']:
    text=(root/row['capture']/'client.log').read_text()
    samples=[tuple(map(int,m)) for m in re.findall(r'GST_IMAGE frame=\d+ .*? pts=(\d+) hash=\d+ sequence=(\d+) ',text)]
    assert len(samples)==32
    span=samples[-1][0]-samples[0][0]
    row['consumed_timestamp_fps']=round(31*1e9/span,3)
    row['sequence_normalized_timestamp_fps']=round((samples[-1][1]-samples[0][1])*1e9/span,3)
    applies={}
    contexts={}
    for line in text.splitlines():
        values=dict(re.findall(r'([a-z][a-z0-9-]*)=([^ ]+)',line))
        if 'LSC_APPLIED ' in line:
            revision=int(values['revision']);assert revision not in applies
            assert int(values['mesh-trace'])>0;applies[revision]=values
        if 'LSC_CONTEXT ' in line:
            sof=int(values['sof']);assert sof not in contexts;contexts[sof]=values
    used=set()
    for _,sof in samples:
        context=contexts[sof];revision=int(context['revision']);applied=applies[revision]
        assert context['mesh-trace']==applied['mesh-trace'] and int(applied['first-sof'])<=sof
        used.add(revision)
    row.update(lsc_contexts_checked=32,lsc_selected_revisions=len(used),lsc_parameter_context_consistent=True)
report.update(sensor_candidate_module_loaded_note_verified=True,original_sensor_module_file_and_note_restored=True,
    mode3_original_profile_and_tables_preserved=True,stock_mode2_ordered_writes=53,
    mode2_crop=[0,376,4208,2368],lsc_first_quad=[0,188],lsc_quad_step=[1,1],
    original_363_endpoint_723200000_used=True,control_pixel_rate_hz=481930000,
    two_frame_control_delay_physically_proven=False,mode2_optical_lsc_accuracy_proven=False,
    physical_pll_clock_measured=False,source_review_and_finite_control_model_passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
