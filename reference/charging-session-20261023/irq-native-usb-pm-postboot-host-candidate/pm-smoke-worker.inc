def pm_smoke():
    out=Path(__file__).resolve().parent
    request=PM_REQUEST['postboot_request']
    assert PM_REQUEST['schema']=='samurai-native-pm-smoke-v1' and request['profile']=='forward_504'
    validate_request(request)
    assert PM_REQUEST['adoption_guard'].startswith('/var/lib/samurai/irq-native-usb-pm-activate-')
    assert Path(PM_REQUEST['adoption_guard']).read_text()==request['new_boot_id']+'\n'
    current=identity();check_identity(current,request['guard'])
    assert current['boot_id']==request['new_boot_id']
    assert Path('/sys/power/mem_sleep').read_text().strip()=='[s2idle]'
    assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip()=='enabled'
    assert json.loads(Path('/var/lib/samurai/gnss-assist/watch-state.json').read_bytes())['active'] is False
    def save(name,value):
        raw=(json.dumps(value,indent=2)+'\n').encode()
        with (out/name).open('xb') as file:file.write(raw);file.flush();os.fsync(file.fileno())
    def stats():return {p.name:p.read_text().strip() for p in Path('/sys/power/suspend_stats').iterdir() if p.is_file()}
    def checked_snapshot(name):
        raw={}
        try:collect(request,raw);result=audit(raw,request)
        except Exception as error:result=dict(passed=False,collection_error=type(error).__name__,message=str(error))
        save(name,dict(raw=raw,result=result))
        assert result['passed'] is True and len(result['checks'])==12 and not result['errors'],result
        return dict(raw=raw,result=result)
    with (out/'mem-once-claim-private.json').open('x') as file:
        json.dump(dict(boot_id=current['boot_id'],mem_write_limit=1,worker_pid=os.getpid()),file);file.flush();os.fsync(file.fileno())
    before=checked_snapshot('before-private.json')
    first=stats();save('stats-before-private.json',first)
    log_before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(log_before)
    phases=out/'phases-private.jsonl'
    def phase(value):
        with phases.open('a') as file:file.write(json.dumps(value)+'\n');file.flush();os.fsync(file.fileno())
    transaction=suspend_once(SysfsPMIO(phase),alarm_delay_seconds=15,minimum_remaining_seconds=4,wakeup_count_timeout_seconds=10)
    save('pm-transaction-private.json',transaction)
    time.sleep(3)
    after=checked_snapshot('after-private.json')
    last=stats();save('stats-after-private.json',last)
    log_after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(log_after)
    delta={key:int(last[key])-int(value) for key,value in first.items() if value.isdigit() and last.get(key,'').isdigit()}
    continuity=log_after.startswith(log_before)
    tail=log_after[len(log_before):] if continuity else b''
    faults={key:tail.count(key.encode()) for key in ['WARNING:','Oops:','refcount_t: underflow','gpu fault:','NGD resume failed','fatal error received','Unhandled context fault:','Kernel panic - not syncing']}
    residency=transaction.get('estimated_residency_seconds')
    passed=bool(transaction['outcome']=='returned' and transaction['mem_write_attempts']==1 and transaction['mem_returned']
                and type(residency) in (int,float) and 10<=residency<=20
                and delta.get('success')==1 and delta.get('fail',0)==0 and continuity and not any(faults.values()))
    result=dict(schema='samurai-native-pm-smoke-result-v1',terminal=True,device_functional_passed=passed,
                transaction=transaction,suspend_stats_delta=delta,dmesg_continuity=continuity,fault_delta=faults,
                before_postboot_checks=12,after_postboot_checks=12,new_boot_preserved=True,
                USB_host_recovery_accepted=False,RTC_exclusive_wakeup_cause_proven=False,whole_device_PM_accepted=False)
    save('result-private.json',result)
    return 0 if passed else 1

if __name__=='__main__':
    try:raise SystemExit(pm_smoke())
    except Exception:
        import traceback
        (Path(__file__).resolve().parent/'failure-private.txt').write_text(traceback.format_exc())
        raise
