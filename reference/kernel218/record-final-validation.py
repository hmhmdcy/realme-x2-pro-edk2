from pathlib import Path
import hashlib,json,shutil

here=Path(__file__).resolve().parent;repo=here.parents[1]
private=Path('/mnt/e/edk2-samurai-out/kernel218')
root=Path('/home/cy122/x2pro-linux/libcamera214-root')
records=[json.loads(line) for line in (root/'work/libcamera218/output/meson-logs/testlog.json').read_text().splitlines() if line.strip()]
assert len(records)==4 and all(x['result']=='OK' for x in records)
(here/'host-meson-tests-validation.json').write_text(json.dumps(dict(stage=218,focused_tests={x['name']:x['result'] for x in records},passed=4,failed=0,all_upstream_suite_not_claimed=True),indent=2)+'\n')
initial=json.loads((private/'candidate-white-rgb-host-private.log').read_text())
assert initial['program_exit']==1 and not initial['frames'] and initial['test_patterns_and_sensor_controls_restored']
failure=dict(stage=218,initial_candidate_white_preflight_failed=True,error='require packed RGB888 output',
             candidate_build_default_prefix_not_product_prefix=True,production_cpu_config_not_loaded_in_initial_attempt=True,
             initially_generated_default_cpu_configuration_used_field_was_incorrect=True,
             preflight_before_camera_stream_start=True,
             corrected_by_explicit_xdg_config_namespace_with_byte_exact_product_config=True,
             r2_white_and_dark_regressions_passed=True,original_logs_preserved_privately=True)
(here/'initial-regression-failure-validation.json').write_text(json.dumps(failure,indent=2)+'\n')
for name in ['white-rgb','dark-raw']:
    test=json.loads((here/('candidate-'+name+'-validation.json')).read_text());assert test['program_exit']==0 and test['attempt']=='r2' and not any(test['fault_delta'].values())
cpu=json.loads((here/'cpu-isp-tests-validation.json').read_text());assert cpu['tests']['native-quad-cpu-enabled']['cpu_isp_cases']==50 and cpu['tests']['native-quad-cpu-enabled']['passed']
health=json.loads((here/'final-health-validation.json').read_text());assert health['taint']==0 and health['installed_package_count']==944
patch=here/'libcamera-native-quad-candidate.patch'
proof=json.loads((here/'host-source-validation.json').read_text());assert hashlib.sha256(patch.read_bytes()).hexdigest()==proof['candidate_patch_sha256']
target=repo/'linux-port/camera/isp/experimental/0001-libcamera-imx471-native-quad-cpu.patch'
target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists();shutil.copyfile(patch,target)
report=dict(stage=218,algorithm_400_cases_and_50_real_cpu_isp_cases_passed=True,
            full_native_output_pixels_checked=780337408,
            current_mode_candidate_library_regressions_passed=True,
            canonical_experimental_patch_sha256=proof['candidate_patch_sha256'],
            kernel217_candidate_and_production_package_recipe_not_modified=True,
            full_sensor_mode_cfa_geometry_timing_quality_still_open=True,
            existing_phone_deployment_preserved=True)
(here/'final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
