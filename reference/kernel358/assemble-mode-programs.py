"""Stage selected factory exposure policies for the future IPA adapter."""
from pathlib import Path
import copy, json

HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel358')
assert json.loads((HERE/'tuning-binding-validation.json').read_text())['passed']
bindings=json.loads((P.parent/'kernel343/bound-mode-configs-private.json').read_text())
factory=json.loads((P.parent/'kernel336/factory-aec-bundle-private.json').read_text())
rows=[]
for binding in bindings:
    variant=binding['variant'];uid=binding['selected']['Arbitration']['uid']
    root=next(r for r in factory[variant]['roots']['Arbitration'] if r['uid']==uid)
    data=root['data'];table=data['expTables'][0]
    assert table==binding['exposure_table']
    rows.append(dict(variant=variant,sensor_mode_index=binding['sensor_mode_index'],sensor_size=binding['sensor_size'],
        usecase=binding['usecase'],context=binding['context'],arbitration_uid=uid,table_index=0,
        table=copy.deepcopy(table),ev_adjustment=dict(enabled=data['enableEVExpTableAdj'],
            cap_gain=data['enableEVGainCapping'],maximum_gain=data['maxEVCappingGain']),
        antibanding=dict(minimum_period_fraction=table['thresAntiBandingMinExpTimePct'],
            fps_method=data['antibandingVsFPSMethod'],minimum_preview_vertical_blanking_ns=data['minPreviewVertBlankTime']),
        runtime_inputs_required=['flicker_period_ns','actual_sensor_gain_limits','actual_sensor_line_and_frame_limits'],
        ipa_adapter_not_integrated=True))
assert len(rows)==14
(P/'mode-exposure-programs-private.json').write_text(json.dumps(rows,indent=2)+'\n')
report=dict(stage=358,selected_mode_usecase_contexts=len(rows),physical_modes=len({(r['variant'],r['sensor_mode_index']) for r in rows}),
    source_mode_and_streaming_table_selection_reused_from343=True,
    same_selected_tables_as_confirmed_mode_bindings=True,threshold_fps_and_blanking_from_same_selected_arbitration_root=True,
    unknown_front_crop_not_assigned_a_factory_mode=True,frequency_detection_not_inferred_from_tuning=True,
    actual_sensor_limits_not_inferred_from_table_knees=True,configuration_is_staged_data_not_an_active_ipa_profile=True,
    installed=False,phone_changed=False,passed=True)
(HERE/'mode-program-binding-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
