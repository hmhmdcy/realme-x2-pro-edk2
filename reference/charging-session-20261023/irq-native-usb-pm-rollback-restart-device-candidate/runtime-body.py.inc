def observe_staged():
    need(_ROLLBACK_MODULE is not None and _CACHE_EXPECTED is not None,'successful original restore source required')
    need(file_sha(LIVE_PATH)==LIVE_SHA,'fixed read-only live library')
    live=runpy.run_path(LIVE_PATH)
    need(file_sha(LIVE_PATH)==LIVE_SHA and live['REGS']==[0,1,2,3,4,5,7,8,9,15,19],'same nondestructive registers')
    start=time.clock_gettime(time.CLOCK_BOOTTIME);state=live['state']()
    ps=Path('/sys/class/power_supply');supply=ps/'mp2650-input'
    def observed(path):
        try:return path.read_text().strip()
        except OSError as error:return {'errno':error.errno}
    protection=Path('/sys/devices/platform/samurai-gauge-protection/protection_state').read_text()
    value=dict(read_start=start,state=state,
        sample={k:int(v) for k,v in (part.split('=') for part in Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())},
        source={k:observed(ps/'samurai-usb-input'/k) for k in ['online','usb_type','current_max','input_current_limit']},
        notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES},
        openrc_started=Path('/run/openrc/started/samurai-charging').exists(),
        protection={k:int(v,0) for k,v in (part.split('=') for part in protection.split())},
        protection_health=(ps/'samurai-gauge-protection/health').read_text().strip(),charge_behaviour=(supply/'charge_behaviour').read_text().strip(),
        limits={k:int((supply/name).read_text()) for k,name in [('input_ua','input_current_limit'),('charge_ua','constant_charge_current'),('cv_pack_uv','constant_charge_voltage')]},
        current_cache=verify_current_cache(_CACHE_EXPECTED))
    value['read_end']=time.clock_gettime(time.CLOCK_BOOTTIME);return value

def staged_health(data,now):
    need(_ROLLBACK_MODULE is not None and _RESTORED_AFTER is not None,'actual successful restore evidence loaded')
    _ROLLBACK_MODULE.safe_stopped(data,now);_ROLLBACK_MODULE.idle(data);_ROLLBACK_MODULE.retained(_RESTORED_AFTER,data)
    need(charging_sample_phase(data['sample'],True) and data['notes']==OLD_NOTES,
         'stopped logical Full and exact resident modules')
    return dict(stage_INHIBIT_reverified=True,source_budget_observation=data.get('source'),
        hardware_input_ua=data['limits']['input_ua'],no_source_budget_increase=True,runtime_validation_accepted=False)
