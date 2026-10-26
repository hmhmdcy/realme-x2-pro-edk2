"""Audit cached mode2 LTM originals; this tool never accesses the phone."""
from pathlib import Path
import hashlib,json,re,struct
HERE=Path(__file__).resolve().parent
path=HERE.parent/'kernel467/inspect-tele.py';raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='64d510506c3b0d90a0031b1af2e0de9479237b4966ab716eddf94c69a64dafed'
source=raw.decode().replace('kernel467','kernel469').replace('stage=467','stage=469')
for old,new in [
 ('41cba861b491d583c685e07fdc0e97d635f8922f7132abefa15d0632d4fab0a4','6396ced1039e352a14c7a07187e780596a3a4180b22391bca0b30f7518db4094'),
 ("plan['original440_profile_preserved']","plan['original440_mode3_preserved']"),
 ("[('2104','1560',str(summary['sensor_mbus_code']))]","[('4208','2368',str(summary['sensor_mbus_code']))]"),
 ('actual_sensor_mode=3,actual_sensor=[2104,1560]','actual_sensor_mode=2,actual_sensor=[4208,2368]'),
 ('assert len(rows)==2','assert len(rows)==1'),
 ("final['direct_completed']==physical","final['direct_completed']==physical+4"),
 ('consumed_images=64','consumed_images=32'),
 ('physical_ipe_completed=physical','physical_ipe_completed=physical+4,live_ipe_completed=physical,replay_ipe_completed=4'),
 ('actual_fd_witnesses=2','actual_fd_witnesses=1'),
 ('all_consumed_images_matched_full_dq=64','all_consumed_images_matched_full_dq=32'),
 ('normal_16_9_mode_verified=False','stock_near_16_9_mode2_stream_verified=True,exact_aspect_center_crop_verified=False'),
 ('tele_independent_ltm_causal_replay_executed=False','tele_independent_ltm_causal_replay_executed=True'),
 ("(HERE/'hardware-validation.json').write_text","(PRIVATE/'base-validation-private.json').write_text"),
 ('print(json.dumps(report,indent=2))','None')]:
    assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new)
exec(compile(source,'retained467-strict-mode2-one-live-case-plus-four-replays','exec'))
proof=json.loads((root/'proof.json').read_bytes());baseline=json.loads((root/'baseline-private.json').read_bytes())
assert state['sensor_module_restored'] and state['candidate_sensor_note']==proof['sensor']['note_sha256']
assert proof['sensor']['sha256']=='494910c99ef116b88038ac3dfcc020a90aa35bfcc610b6b37c152601ee758392'
assert state['sensor_formal_before']==baseline['tele_sensor']
assert plan['sensor_mode']==2 and plan['actual_sensor']==[4208,2368] and plan['cases']==['1280x720-isolated']
assert handoff['window_id']==plan['window_id']==state['tele_window_id']=='k469-tele-ltm-r1'
# The legacy worker prefix retains its stage=467 display field. Actual identity
# is established above by the unique plan/handoff/namespace and payload hashes.
assert state['stage']==467
case=root/'1280x720-replay';capture=root/'1280x720-isolated'
replay=state['replays']['1280x720'];assert replay['passed'] and replay['ipe_completed']==4
sof=replay['source_sof'];pairs=[('full-private.bin','-full.nv12',1382400),('pd10-private.bin','-coarse.pd10',123648),('parameters-private.bin','-params.bin',6008)]
for name,suffix,length in pairs:
    value=(case/name).read_bytes();assert len(value)==length and value==(capture/'captures'/f'tone-{sof}{suffix}').read_bytes()
full=(case/'full-private.bin').read_bytes();coarse=(case/'pd10-private.bin').read_bytes();params=(case/'parameters-private.bin').read_bytes()
assert struct.unpack_from('<II',params)==(1,6008)
outputs=[(case/f'mode-{i}-output-private.bin').read_bytes() for i in range(4)]
assert all(len(x)==1382400 for x in outputs) and outputs[0]==outputs[3] and len(set(outputs[:3]))==3

def fnv(raw):
    value=1469598103934665603
    for byte in raw:value=((value^byte)*1099511628211)&((1<<64)-1)
    return value
jobs=[json.loads(line) for line in (case/'client.log').read_text().splitlines() if line.startswith('{')]
assert jobs==replay['jobs'] and [row['mode'] for row in jobs]==[0,1,2,3]
for i,job in enumerate(jobs):
    expected=bytearray(coarse)
    if i in [1,2]:
        for row in range(90):
            for group in range(160):
                off=row*1344+group*8
                expected[off:off+8]=bytes([0 if i==1 else 255]*4+[128,128,0 if i==1 else 255,0])
    assert job['passed'] and job['full_hash']==f'{fnv(full):016x}' and job['pd10_hash']==f'{fnv(expected):016x}'
    assert job['output_hash']==f'{fnv(outputs[i]):016x}'
    scratch=(case/f'mode-{i}-scratch-private.bin').read_bytes();assert len(scratch)==121024
    version,length,crc,changed=struct.unpack_from('<IIII',scratch)
    assert (version,length,crc,changed)==(1,121008,job['scratch_crc'],job['scratch_changed_bytes'])
images=re.findall(r'GST_IMAGE frame=\d+ width=1280 height=720 bytes=1382400 pts=\d+ hash=(\d+) sequence='+str(sof)+r' wall-ns=\d+',(capture/'client.log').read_text())
assert len(images)==1 and int(images[0])==fnv(outputs[0][::len(outputs[0])//4096])
assert replay['source_consumed_sample_hash_equal'] and not replay['source_output_full_byte_compare']
report.update(sensor_candidate_module_loaded_note_verified=True,original_sensor_module_file_and_note_restored=True,
    original_mode2_profile_reused=True,source_sof=sof,source_epoch=replay['epoch'],source_token=replay['token'],source_revision=replay['revision'],
    ltm_replay_order=['real','black','white','same-real'],full_and_parameters_fixed=True,independent_expected_pd10_and_output_hashes_verified=True,
    three_distinct_full_outputs=True,real_repeat_full_byte_equal=True,actual_consumer_sample_hash_matches_real_replay=True,
    actual_consumer_full_byte_comparison_performed=False,scratch_crc_varied=len({job['scratch_crc'] for job in jobs})>1,
    scratch_changed_bytes=[job['scratch_changed_bytes'] for job in jobs],scratch_mutation_used_as_consumption_evidence=False,
    sensor_mode2_control_apply_delay_proven=False,mode2_optical_lsc_accuracy_proven=False,goal_complete=False,
    legacy_worker_stage_field_preserved=467,identity_uses_plan_handoff_payload_and_namespace=True)
(HERE/'hardware-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
