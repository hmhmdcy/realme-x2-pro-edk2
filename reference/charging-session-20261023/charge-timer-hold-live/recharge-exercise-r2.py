"""Bounded normal-service discharge/recharge observation, inert on import."""
def observe_recharge(io, timer, maximum_seconds=5400):
    assert type(maximum_seconds) is int and 20<=maximum_seconds<=5400
    result=dict(schema='samurai-full-recharge-live-v2',passed=False,error=None,cleanup_error=None,
        stop_attempted=False,stop_confirmed=False,resume_attempted=False,resume_confirmed=False,
        threshold_uv=4200000,threshold_reached=False,stop_reason=None,discharge_samples=[],resumed_samples=[],timer=None,
        full_state_cleared_by_operator=False,voltage_target_changed=False,physical_detach_tested=False)
    stopped=False
    def resume_once():
        fresh=io.observe();io.validate(fresh)
        assert fresh['behaviour']=='inhibit-charge' and fresh['register08']&0x18==8
        result['resume_attempted']=True
        io.command('resume')
        io.sleep(2);fresh=io.observe();io.validate(fresh)
        assert fresh['behaviour']=='auto';result['resume_confirmed']=True;result['resumed_samples'].append(fresh)
    try:
        before=io.observe();result['before']=before;io.validate(before)
        assert before['behaviour']=='auto' and before['sample']['logical_full']==before['sample']['full_holding']==1
        assert before['sample']['session_seconds']==0
        result['stop_attempted']=True;io.command('stop')
        fresh=io.observe();io.validate(fresh)
        assert fresh['behaviour']=='inhibit-charge' and fresh['register08']&0x18==8
        stopped=True;result['stop_confirmed']=True
        start=io.now();deadline=start+maximum_seconds
        while True:
            fresh=io.observe();io.validate(fresh);s=fresh['sample']
            assert fresh['behaviour']=='inhibit-charge' and fresh['register08']&0x18==8
            assert s['logical_full']==1 and s['full_cause']==before['sample']['full_cause'] and s['session_seconds']==0
            result['discharge_samples'].append(fresh)
            io.save('status-private.json',dict(phase='natural_discharge',boottime=io.now(),maximum_seconds=maximum_seconds,
                elapsed_seconds=io.now()-start,last=fresh,threshold_uv=result['threshold_uv']))
            if max(s['cell1_uv'],s['cell2_uv'])<=result['threshold_uv']:
                result['threshold_reached']=True;result['stop_reason']='voltage_threshold';break
            if io.cancelled():result['stop_reason']='cancelled';break
            if io.now()>=deadline:result['stop_reason']='bounded_timeout';break
            if io.now()-start>=300:
                values=result['discharge_samples'];initial=max(before['sample']['cell1_uv'],before['sample']['cell2_uv'])
                if not any(v['sample']['gauge_current_ua'] < -5000 for v in values) and initial-max(s['cell1_uv'],s['cell2_uv'])<5000:
                    result['stop_reason']='no_measured_discharge';break
            io.sleep(min(10,deadline-io.now()))
        result['discharge_seconds']=io.now()-start
        resume_once()
        if result['threshold_reached']:
            deadline=io.now()+150
            while io.now()<deadline:
                fresh=io.observe();io.validate(fresh);result['resumed_samples'].append(fresh)
                io.save('status-private.json',dict(phase='recharge_wait',boottime=io.now(),last=fresh,threshold_uv=result['threshold_uv']))
                assert fresh['behaviour']=='auto'
                if fresh['sample']['logical_full']==0 and fresh['sample']['desired_enable']==1 and fresh['sample']['session_seconds']>=8:
                    result['recharge_observed']=True
                    io.save('status-private.json',dict(phase='timer_hold',boottime=io.now(),last=fresh))
                    result['timer']=timer(io,60)
                    break
                if io.cancelled():break
                io.sleep(2)
    except BaseException as error:result['error']=repr(error)
    finally:
        # Exactly one resume request for this initial stop, including cleanup.
        # The nested timer exercise owns its own later stop/resume pair.
        if stopped and not result['resume_attempted']:
            try:resume_once()
            except BaseException as error:result['cleanup_error']=repr(error)
    result['passed']=bool(result.get('recharge_observed') and result['timer'] and result['timer']['passed'] and
        result['resume_confirmed'] and result['error'] is None and result['cleanup_error'] is None)
    return result
