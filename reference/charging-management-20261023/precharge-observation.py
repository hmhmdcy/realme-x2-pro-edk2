"""Bounded battery observation using only the normal stop/resume controls.

Inert on import. The device adapter owns identity, limits, health and the service
lock. Register reads exclude the destructive fault register. No threshold,
current, voltage, gauge command, or protection setting is changed here.
"""


def observe_precharge(io, maximum_discharge_seconds=28800,
                      maximum_recharge_seconds=3500, *, full_start_required=True):
    if not (type(maximum_discharge_seconds) is int and
            20 <= maximum_discharge_seconds <= 28800 and
            type(maximum_recharge_seconds) is int and
            10 <= maximum_recharge_seconds <= 3500 and
            type(full_start_required) is bool):
        raise ValueError('invalid observation duration')
    result = dict(passed=False, stop_attempted=False, stop_confirmed=False,
                  resume_attempted=False, auto_restored=False,
                  discharge_target_uv=3300000, minimum_cell_cutoff_uv=3250000,
                  precharge_seen=False, constant_current_seen=False,
                  error=None, cleanup_error=None, reason=None,
                  charge_parameters_changed=False, physical_detach_tested=False)
    result.update(full_start_required=full_start_required,
                  initial_logical_full=None, initial_session_seconds=None,
                  stopped_session_seconds=None)

    def observe(phase):
        v = io.observe()
        io.validate(v)
        s = v['sample']
        cells = s['cell1_uv'], s['cell2_uv']
        if min(cells) < 3200000 or abs(cells[0] - cells[1]) > 30000:
            raise RuntimeError('cell floor or imbalance observation limit')
        if not 180 <= s['temp_decic'] < 400:
            raise RuntimeError('observation temperature limit')
        io.record(phase, v)
        return v

    def restore_auto():
        # Observe the selected mode before a cleanup request: a lost ACK must
        # not turn an already applied resume into another control transaction.
        v = io.observe()
        if v['behaviour'] != 'auto':
            result['resume_attempted'] = True
            io.command('resume')
        v = io.observe()
        if v['behaviour'] != 'auto':
            raise RuntimeError('AUTO readback failed')
        result['auto_restored'] = True
        return v

    try:
        before = observe('before')
        s = before['sample']
        if before['behaviour'] != 'auto':
            raise RuntimeError('requires healthy AUTO')
        if full_start_required and not (s['logical_full'] == 1 and
                s['full_holding'] == 1 and s['session_seconds'] == 0):
            raise RuntimeError('requires a healthy completed Full cycle')
        if not full_start_required and not s['logical_full'] and not (
                s['desired_enable'] == 1 and before['register08'] & 0x18 == 0x10):
            raise RuntimeError('requires enabled healthy AUTO or completed Full')
        result['initial_logical_full'] = s['logical_full']
        result['initial_session_seconds'] = s['session_seconds']
        result['full_cause_before'] = s['full_cause']
        result['stop_attempted'] = True
        io.command('stop')
        start = io.now()
        deadline = start + maximum_discharge_seconds
        # The driver's first later sample bills the actual stop/readback time.
        # Let it settle before pinning a nonzero paused counter. Full starts
        # retain their original immediate zero-counter check.
        if not full_start_required:
            io.sleep(5)
        negative_current_seen = False
        while True:
            v = observe('discharge')
            s = v['sample']
            if v['behaviour'] != 'inhibit-charge' or v['register08'] & 0x18 != 8:
                raise RuntimeError('normal stop not confirmed')
            result['stop_confirmed'] = True
            if result['stopped_session_seconds'] is None:
                if (full_start_required and s['session_seconds'] != 0 or
                        not full_start_required and
                        s['session_seconds'] < result['initial_session_seconds']):
                    raise RuntimeError('stopped counter reset or invalid Full counter')
                result['stopped_session_seconds'] = s['session_seconds']
            if not (s['logical_full'] == result['initial_logical_full'] and
                    s['full_cause'] == result['full_cause_before'] and
                    s['session_seconds'] == result['stopped_session_seconds']):
                raise RuntimeError('stopped state or paused counter changed')
            negative_current_seen |= s['gauge_current_ua'] < -5000
            cells = s['cell1_uv'], s['cell2_uv']
            if max(cells) <= result['discharge_target_uv']:
                result['reason'] = 'voltage_target'
                break
            if min(cells) <= result['minimum_cell_cutoff_uv']:
                result['reason'] = 'minimum_cell_cutoff'
                break
            if io.cancelled():
                result['reason'] = 'cancelled'
                break
            if io.now() >= deadline:
                result['reason'] = 'discharge_deadline'
                break
            if io.now() - start >= 300 and not negative_current_seen:
                result['reason'] = 'no_measured_discharge'
                break
            io.sleep(min(10, deadline - io.now()))
        result['discharge_seconds'] = io.now() - start
        restore_auto()
        if result['reason'] not in ('voltage_target', 'minimum_cell_cutoff'):
            return result
        start = io.now()
        deadline = start + maximum_recharge_seconds
        consecutive_cc = 0
        while True:
            v = observe('recharge')
            s = v['sample']
            if v['behaviour'] != 'auto':
                raise RuntimeError('AUTO changed during observation')
            phase = (v['register13'] >> 2) & 3
            active = s['desired_enable'] == 1 and v['register08'] & 0x18 == 0x10
            if active and phase == 1 and s['gauge_current_ua'] > 0:
                result['precharge_seen'] = True
            cc = active and phase == 2 and s['gauge_current_ua'] > 0
            consecutive_cc = consecutive_cc + 1 if cc else 0
            if result['precharge_seen'] and consecutive_cc >= 2:
                result['constant_current_seen'] = True
                result['reason'] = 'precharge_to_constant_current'
                break
            if io.cancelled():
                result['reason'] = 'cancelled_after_resume'
                break
            if io.now() >= deadline:
                result['reason'] = 'recharge_deadline'
                break
            io.sleep(min(0.25 if io.now() - start < 15 else 2,
                         deadline - io.now()))
        result['recharge_seconds'] = io.now() - start
    except BaseException as error:
        result['error'] = repr(error)
    finally:
        if result['stop_attempted']:
            try:
                restore_auto()
            except BaseException as error:
                result['cleanup_error'] = repr(error)
    result['passed'] = bool(result['precharge_seen'] and
                            result['constant_current_seen'] and
                            result['auto_restored'] and
                            result['error'] is None and
                            result['cleanup_error'] is None)
    return result
