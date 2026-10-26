"""Make a redacted receipt from the finite original-instruction AF override cases."""
from pathlib import Path
import hashlib
import json
import struct
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel460')
SOURCE=PRIVATE.parent/'kernel453/af-config-source'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    library=json.loads((PRIVATE/'native-config-trial-private.json').read_text())
    hal=json.loads((PRIVATE/'native-hal-override-proof-private.json').read_text())
    ltrace=json.loads((PRIVATE/'native-library-trace-private.json').read_text())
    htrace=json.loads((PRIVATE/'native-hal-trace-private.json').read_text())
    assert len(ltrace['pcs'])==library['instructions']==33261
    assert len(htrace['pcs'])==hal['instructions']==5487
    assert library['key_count']==library['values_count']==4 and len(library['rows'])==4
    assert all(row['result']==0 and len(row['values'])==4 for row in library['rows'])
    assert library['independent_text_crosscheck_equal'] and library['missing_locale_failed']
    assert library['missing_key_count_zero'] and library['truncated_output_native_min_count']
    assert library['failed_file_load']['no_fallback'] and len(library['failed_file_load']['open_attempts'])==1
    assert library['loads']==[dict(path='/odm/etc/camera/CameraHWConfiguration.config',mode='r')]
    assert library['failed_file_load']['open_attempts']==library['loads']
    assert hal['all_bounds_and_step_values_equal_retained453']
    assert all(sha(path)==digest for path,digest in hal['protected_files_before'].items())
    assert [row['api'] for row in hal['calls']]==['GetKeyCount','GetValuesCount','GetLocaleIntegerListConfiguration','GetLocaleIntegerListConfiguration']
    assert [row['locale'] for row in hal['calls'][2:]]==['0','1']
    assert all(row['result']==0 and row['count']==4 for row in hal['calls'][2:])
    assert all(pc in htrace['pcs'] for pc in [0x4f7e8c,0x4f7eb0,0x4f8304,0x4f83f0,0x4f8474])
    assert not any(pc in htrace['pcs'] for pc in [0x4f803c,0x4f82a4])
    raw=(SOURCE/'libhwconfigurationutil-r6.so').read_bytes()
    phoff=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
    segments=[struct.unpack_from('<II6Q',raw,phoff+i*stride) for i in range(count)]
    def code(address,length):
        off=next(off+address-va for kind,flags,off,va,pa,filesz,memsz,align in segments if kind==1 and va<=address and address+length<=va+filesz)
        return raw[off:off+length]
    ranges=[dict(name=name,begin=hex(begin),end_exclusive=hex(end),sha256=hashlib.sha256(code(begin,end-begin)).hexdigest())
            for name,begin,end in [('HWConfigurationUtil default loader segment',0x15e68,0x15eb0),
                                   ('KeyFile::Create',0xdab0,0xdba8),
                                   ('KeyFile::KeyFileLoadFromFile and adjacent logger',0xc158,0xc658),
                                   ('LineParser::ParseLine',0x157d8,0x1593c),
                                   ('KeyFileKeyValuePair::ParseLine',0x12640,0x12b74),
                                   ('KeyFile::KeyFileGetLocaleIntegerList',0x10000,0x101e8),
                                   ('KeyFile::KeyFileParseValueAsInteger',0xe6b8,0xe7dc)]]
    report=dict(stage=460,scope='matching default ODM AF boundary override, retained Qtech S5K3M5SX mode3',
                inputs=dict(hal_sha256=hal['hal_sha256'],library_sha256=library['library_sha256'],library_bytes=len(raw),
                            configuration_sha256=library['configuration_sha256'],configuration_bytes=(SOURCE/'CameraHWConfiguration-r6.config').stat().st_size,
                            matching_hal_gate_from_retained_sources=True,readonly_odm_debugfs_source=True,
                            mounted_or_executed_oem_on_phone=False,new_eeprom_reads=False),
                default_loading=dict(path=library['loads'][0]['path'],mode='r',fixed_constructor_source=True,
                                     attempted_paths_in_success_case=1,attempted_paths_in_missing_file_case=1,
                                     alternative_vendor_data_fallback_in_inspected_default_path=False,
                                     missing_file_produces_null_keyfile_and_key_count_zero=True,
                                     android_namespace_filesystem_overlays_and_runtime_file_identity_not_executed=True),
                parsing=dict(actual_target_line_and_keyvalue_parser_executed=True,actual_target_hash_lookup_and_api_getters_executed=True,
                             group='OemCamActuatorSettingMap',key_count=4,locale_key_pattern='Mode[n]',locale_indices=[0,1,2,3],
                             integer_counts_per_locale=[4,4,4,4],delimiter='semicolon',inline_comments_present_in_actual_file=True,
                             independent_text_model_used_only_as_crosscheck=True,missing_locale_returns_failure=True,
                             missing_key_count_zero=True,short_destination_uses_native_min_count_with_canary=True,
                             integer_conversion_external_provider='host libc strtol; native target checks suffix and stores int32',
                             target_library_instruction_count=library['instructions'],original_code_ranges=ranges),
                hal_af=dict(native_begin=hal['native_begin'],native_end_exclusive=hal['native_end_exclusive'],
                            native_instructions=hal['instructions'],actual_descriptor_actuator_type=0,actual_descriptor_bit_width=10,
                            requires_exactly_four_group_keys=True,values_count_key='Mode[0]',
                            chosen_locales=['0','1'],chosen_list_getters_succeeded=True,
                            original_upper_lower_calculation_executed=True,
                            lower_upper_equal_prior_conditional_inputs=True,initial_code_equal=True,code_per_step_equal=True,
                            every_step_equal=True,step_count=len(hal['step_table']),
                            prior453_source_receipts_candidates_and_nominal_files_unchanged=True,
                            no_generalization_to_other_actuator_types_modes_or_runtime_overlays=True),
                execution_limits=dict(original_default_constructor_load_segment_executed_to='0x15eb0',
                                      constructor_diagnostic_dump_and_statistics_sweep_not_executed=True,
                                      api_singleton_storage_bound_to_loaded_object_using_observed_layout=True,
                                      std_cpp_getline_and_filebuf_close_are_explicit_providers=True,
                                      cpp_string_locale_allocation_and_exact_type_cast_providers_are_bounded_models=True,
                                      not_full_android_loader_or_cpp_runtime_validation=True,
                                      zero_host_file_writes_through_oem_stdio=True),
                remaining=dict(factory_af_checksum_and_acceptance_verified=False,supplier_identity_certified=False,
                               static_runtime_sag_gate_verified=False,live_gravity_or_orientation_verified=False,
                               optical_response_fom_search_bounds_or_settle_timing_verified=False,
                               actual_android_process_configuration_selected_at_runtime_verified=False),
                initial_rejected_trials=dict(count=3,causes=['assumed fopen rb; actual mode r',
                     'missing C++ ios getloc provider','codecvt close abort with deliberately incomplete C++ environment'],
                     final_filebuf_close_provider_explicit=True,not_counted_as_passed_cases=True),
                coefficients_raw_unit_fingerprints_addresses_and_instruction_traces_private=True,
                new_candidate_or_production_parameters_written=False,deployable=False,applied=False,
                no_phone_ssh_sdk_build_network_or_deployment=True,
                scripts={name:sha(HERE/name) for name in ['native-config.py','inspect-override.py','finalize.py']},
                offline_checks_passed=True)
    (HERE/'override-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (PRIVATE/'rejected-trials-private.json').write_text(json.dumps(report['initial_rejected_trials'],indent=2)+'\n')
    print(json.dumps(dict(stage=460,offline_checks_passed=True,all453_clip_and_step_values_unchanged=True,
                          full_android_runtime_verified=False,checksum_verified=False,deployable=False)))


if __name__=='__main__':main()
