"""Bounded normal-service INHIBIT/AUTO experiment; inert on import."""
def exercise(io, duration=60):
    if type(duration) is not int or not 20 <= duration <= 75:
        raise ValueError('bounded observation duration')
    result=dict(schema='samurai-confirmed-stop-timer-live-v1',passed=False,stop_attempted=False,
        stop_confirmed=False,resume_attempted=False,resume_confirmed=False,error=None,cleanup_error=None,
        paused_samples=[],resumed_samples=[],cycle_latches_cleared=False,physical_detach_tested=False)
    stopped=False
    try:
        before=io.observe();io.validate(before)
        assert before['behaviour']=='auto' and before['sample']['desired_enable']==1
        assert before['sample']['logical_full']==0 and before['sample']['session_seconds']>0
        result['before']=before;result['stop_attempted']=True
        io.command('stop')
        first=io.observe();io.validate(first)
        assert first['behaviour']=='inhibit-charge' and first['register08']&0x18==8
        stopped=True;result['stop_confirmed']=True;result['stopped']=first
        # The first collection after synchronous readback may still contain
        # the preceding sample. Allow one actual driver period before anchor.
        io.sleep(2)
        anchor=io.observe();io.validate(anchor)
        assert anchor['behaviour']=='inhibit-charge' and anchor['register08']&0x18==8
        assert anchor['sample']['logical_full']==0 and anchor['sample']['desired_enable']==0
        assert 0 <= anchor['sample']['session_seconds']-before['sample']['session_seconds'] <= 3
        result['anchor']=anchor;deadline=io.now()+duration
        while True:
            value=io.observe();io.validate(value)
            assert value['behaviour']=='inhibit-charge' and value['register08']&0x18==8
            assert value['sample']['logical_full']==0 and value['sample']['desired_enable']==0
            assert value['sample']['session_seconds']==anchor['sample']['session_seconds']
            result['paused_samples'].append(value)
            if io.now()>=deadline:break
            io.sleep(min(2,deadline-io.now()))
        result['pause_seconds']=result['paused_samples'][-1]['boottime']-result['paused_samples'][0]['boottime']
        assert result['pause_seconds']>=duration-1
        result['pause_verified']=True
    except BaseException as error:
        result['error']=repr(error)
    finally:
        if stopped:
            try:
                fresh=io.observe();io.validate(fresh)
                assert fresh['behaviour']=='inhibit-charge' and fresh['register08']&0x18==8
                result['resume_attempted']=True
                io.command('resume')
                # Normal kernel AUTO retains policy/Full/fault gates. This is
                # not a direct enable-register write or a fault reset.
                for index in range(6):
                    io.sleep(2)
                    fresh=io.observe();io.validate(fresh)
                    assert fresh['behaviour']=='auto'
                    assert fresh['sample']['desired_enable']==1 or fresh['sample']['full_holding']==1
                    result['resumed_samples'].append(fresh)
                result['resume_confirmed']=True
                if all(not v['sample']['logical_full'] for v in result['resumed_samples']):
                    seconds=[v['sample']['session_seconds'] for v in result['resumed_samples']]
                    assert seconds[-1]-seconds[0]>=8 and seconds[0]>=result['anchor']['sample']['session_seconds']
                    result['active_accumulation_resumed']=True
                else:
                    result['active_accumulation_resumed']=False
                    result['healthy_Full_during_resume']=True
            except BaseException as error:
                result['cleanup_error']=repr(error)
    result['passed']=bool(result.get('pause_verified') and result['resume_confirmed'] and result['error'] is None and result['cleanup_error'] is None)
    return result
