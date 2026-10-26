"""Bind cached mode queries, stock-manager provenance and next consumers.

Does not re-run the stock manager, capture hardware, bind the SDK or build.
"""
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel465')
P = PRIVATE.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

analysis = json.loads((PRIVATE / 'tele-mode-analysis-private.json').read_text())
receipt = json.loads((HERE / 'tele-mode-validation.json').read_text())
assert receipt['passed']
assert sha(P / 'kernel306/qtech-s5k3m5sx-tuning-private.bin') == receipt['tuning_sha256']
assert sha(P / 'kernel343/stock-selection-manager') == receipt['manager_sha256']
for source in analysis['sources']:
    assert sha(P / source['path']) == source['sha256']
mapping = {'TYPES':'parametertypes.h','UTILS':'parameterutils.h','MODULE':'parametermodule.h','MANAGER':'parametersetmanager.h',
           'ENTRY':'parameterfilesymboltableentry.h','TABLE':'parameterfilesymboltable.h','TTYPES':'parametertuningtypes.h'}
template = json.loads((P / 'kernel343/manager-template-private.json').read_text())
manager_sources = []
for row in template['templates']:
    if row['file'].endswith('.partial'):
        continue
    original = P / 'kernel343/sources' / row['file']
    assert sha(original) == row['sha256']
    text = original.read_text()
    for key, value in mapping.items():
        text = text.replace('$' + key + '$', value)
    actual = P / 'kernel343/manager-build' / row['file']
    assert actual.read_text() == text
    manager_sources.append(dict(name=row['file'], template_sha256=row['sha256'], compiled_source_sha256=sha(actual)))

queries = analysis['complete_selections']
tags = sorted(set(r['tag'] for r in queries))
expected = [(tag, [0, mode, usecase, 0, 0, 0, 0]) for mode in [2, 3] for usecase in [0, 2] for tag in tags]
assert [(r['tag'], r['context']) for r in queries] == expected
lines = (PRIVATE / 'stock-selection-private.log').read_text().splitlines()
assert len(lines) == len(queries) == 516
for index, (row, line) in enumerate(zip(queries, lines)):
    selected = row['selection']
    assert line.split() == [str(index), row['tag'], str(selected['uid'] if selected else 0), str(selected['mode_id'] if selected else 0)]
by_context = {}
for row in queries:
    by_context.setdefault(tuple(row['context']), {})[row['tag']] = row['selection']
contexts = list(by_context.values())
assert all(context == contexts[0] for context in contexts[1:])
key_tags = ['Metering', 'Arbitration', 'lsc34_ife', 'cc12_ife', 'MWBGainV1', 'refPtV1', 'sensorCalV1',
            'ds4to1v10_ife_full_dc4', 'gtm10_ife', 'tmc10_sw', 'tmc11_sw', 'ltm13_ipe', 'cc13_ipe', 'gamma16_ife', 'gamma15_ipe']
selected_ids = {tag:dict(uid=contexts[0][tag]['uid'],mode_id=contexts[0][tag]['mode_id']) for tag in key_tags if contexts[0].get(tag)}
sources = json.loads((PRIVATE / 'csi-reference-sources-private.json').read_text())
selection = dict(stage=465, retained_binary_sha256=receipt['tuning_sha256'], retained_manager_sha256=receipt['manager_sha256'],
                 manager_template_parser_sha256=template['parser_sha256'],
                 original_functions=['ParameterSetManager::LoadBinaryParameters', 'ParameterSetManager::ReadSections', 'ParameterSetManager::GetModeEntry', 'ParameterSetManager::GetModule'],
                 manager_template_sources_match_except_filename_placeholders=True,
                 manager_sources=manager_sources,
                 manager_payload_provider='Generic::Parse retains ID, name and ModeId; IQ payload parse is stubbed',
                 manager_is_host_build_of_recovered_templates_not_target_android_hal_execution=True,
                 independent_method='ModeTree reads the retained aligned v1.1 binary section2 nodes and section0 module ModeId, then follows all seven explicit context axes',
                 axes=['Default','Sensor','Usecase','Feature1','Feature2','Scene','Effect'],
                 contexts=[[0,2,0,0,0,0,0],[0,2,2,0,0,0,0],[0,3,0,0,0,0,0],[0,3,2,0,0,0,0]],
                 usecase_values={'Preview':0,'Video':2}, queried_tags=len(tags), queries=len(queries),
                 selected_nonnull_tags=sum(value is not None for value in contexts[0].values()),
                 all_129_tags_same_object_across_four_contexts=True,
                 original_manager_and_independent_results_differences=0, selected_key_ids=selected_ids,
                 cached_stdout_sha256=sha(PRIVATE / 'stock-selection-private.log'),
                 independent_reader_sha256=sha(HERE.parent / 'kernel343/mode_tree.py'),
                 reference_csi_sources=sources, actual_android_runtime_tuning_metadata_observed=False,
                 coefficients_published=False, new_manager_build=False, phone_accessed=False, passed=True)
(HERE / 'selection-validation.json').write_text(json.dumps(selection, indent=2) + '\n')

artifacts = []
for relative, expected_sha, purpose in [
    ('kernel461/libcamera.so.0.7.2','9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af','core'),
    ('kernel449/gst-sustained','7f4d6a1f8527280d8bbe11e6af638348200bd9bc8465be8357cdc0ca732b852a','normal-consumer'),
    ('kernel449/pipeline-fixture-long','bad0dc79d95d070f089c158b159a21f72a44a459f4c1606f9c27493457863a43','restoring-fixture'),
    ('kernel442/capture','052cdeb9aa7d1b6c4140067ccd45604fdddc9dc4f02adf2a5d8b608e9625ffb6','optional-trace-capture'),
    ('kernel441/pd10-ipe','5be7faeb481c68996e57f476889f5e51d1af550922d0c0ba809b6b5c5daac5f2','optional-causal-replay'),
    ('kernel440/factory-s5k3m5-private.yaml','41cba861b491d583c685e07fdc0e97d635f8922f7132abefa15d0632d4fab0a4','existing-mode3-profile'),
]:
    path = P / relative
    assert sha(path) == expected_sha
    artifacts.append(dict(private_relative_path=relative, bytes=path.stat().st_size, sha256=expected_sha, purpose=purpose))
plan = dict(stage=465, executable_or_deployment_script=False, ready_mode3_consumer_inputs=artifacts,
            retained_ipa_stage=444, retained_ipa_protocol=6, retained_proxy='old444', retained_kernel_geometry_stage=441,
            model='s5k3m5', required_active_sensor=[2104,1560], sensor_mode=3,
            user=10000, effective_capabilities=0, isolation=True,
            minimum_target_frames=32, normal_consumer_program='gst-sustained',
            normal_consumer_arguments=['${fresh_camera_id}', '${width}', '${height}'],
            environment={'GST_TARGET_FRAMES':'32', 'GST_SENSOR_NODE':'${fresh_sensor_node}', 'LIBCAMERA_IPA_FORCE_ISOLATION':'1', 'LIBCAMERA_CAMSS_VFE_PROFILE':'${userroot}/factory-s5k3m5-private.yaml'},
            existing_user_launcher='reference/kernel449/user-launcher.py', launcher_requires_userroot_prefix='/run/user/10000/k449-user-',
            output_cases=[dict(width=1280,height=720,full_bytes=1382400,pd10=[320,180],pd10_stride=1344,pd10_slice_height=92,pd10_bytes=123648,scratch_bytes=121008),
                          dict(width=1920,height=1080,full_bytes=3110400,pd10=[480,270],pd10_stride=1920,pd10_slice_height=136,pd10_bytes=261120,scratch_bytes=261168)],
            require_actual_full_fd_selection='reference/kernel463/full-role.py with fresh graph, FD identity and event emission',
            audit_source='reference/kernel449/check-long.py raw frame/receipt audit and 450 strict wrapper; adapt model, sizes, frame target and witnesses in a new checker only',
            optional_tele_causal=dict(capture_program='capture', capture_arguments=['s5k3m5','${fresh_sensor_node}','2104x1560','0','1280x720'],
                                      application_queue={'CAPTURE_QUEUED':'1','CAPTURE_DELAY_MS':'0'},
                                      trace_environment='LIBCAMERA_CAMSS_VFE_TRACE_DIR=${new_private_case}',
                                      source_files=['tone-${sof}-full.nv12','tone-${sof}-coarse.pd10','tone-${sof}-params.bin'], params_bytes=6008,
                                      replay_program='pd10-ipe', replay_arguments=['${fresh_ipe_video}','${fresh_ipe_media}','${private_replay_case}','1280','720','121008'],
                                      replay_input_names=['full-private.bin','pd10-private.bin','parameters-private.bin'],
                                      ordered_pd10_inputs=['real','neutral-black','neutral-white','same-real'],
                                      expected_real_repeat_equal=True, expected_three_distinct_outputs=True,
                                      adapt_from='reference/kernel442/auto-capture-body.py; never restart its terminal worker',
                                      mandatory_if_claiming_tele_specific_causal_consumption=True),
            new_mode2_not_ready=True, normal_16_9_geometry_completed=False,
            phone_accessed=False, staged=False, executed=False, passed=True)
(HERE / 'consumer-plan.json').write_text(json.dumps(plan, indent=2) + '\n')

inputs = [path for path in sorted(HERE.iterdir()) if path.is_file() and path.name != 'frozen-validation.json']
frozen = dict(stage=465, selection_validation_passed=True, source_payloads_kept_private=True,
              public_files=[dict(name=path.name,bytes=path.stat().st_size,sha256=sha(path)) for path in inputs],
              private_analysis_sha256=sha(PRIVATE / 'tele-mode-analysis-private.json'),
              private_query_stdout_sha256=sha(PRIVATE / 'stock-selection-private.log'),
              phone_accessed=False,sdk_bound=False,new_build=False,passed=True)
(HERE / 'frozen-validation.json').write_text(json.dumps(frozen, indent=2) + '\n')
print(json.dumps(dict(stage=465, files=len(inputs), stock_queries=516, nonnull_tags=selection['selected_nonnull_tags'], consumer_artifacts=len(artifacts), passed=True), indent=2))
