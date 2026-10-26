"""One RTC-backed suspend of the accepted505 cohort; the caller prefixes the tested primitive and scoped trace."""
def run_pm():
    out=Path(__file__).resolve().parent
    def save(name,value):
        with (out/name).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    def snapshot():
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='839fa852-0f09-4e58-8381-50557631b10a'
        assert '#506 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026' in Path('/proc/version').read_text()
        assert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()=='73b09373a47374612ef7451fd1890186bbbddd486612f888dab1be0b9d827b02'
        assert Path('/proc/sys/kernel/tainted').read_text().strip()=='4096'
        sample={k:int(v) for k,v in (word.split('=') for word in Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())}
        assert sample['valid']==sample['online']==sample['protection_ok']==1 and sample['budget_ua']==500000
        assert all(sample[k]==0 for k in ['error','stop_error','fault','latched','thermal_inhibit','cycle_timeout','source_inhibit'])
        psy=Path('/sys/class/power_supply/mp2650-input')
        assert (psy/'health').read_text().strip()=='Good' and '[auto]' in (psy/'charge_behaviour').read_text()
        assert [(psy/name).read_text().strip() for name in ['input_current_limit','constant_charge_current','constant_charge_voltage']]==['500000','250000','8725000']
        cache=Path('/sys/devices/platform/samurai-gauge-protection/mac_evidence').read_bytes()
        first=dict(x.split('=',1) for x in cache.decode().splitlines()[0].split());assert first['attempted']==first['terminal']=='0'
        return dict(boot=boot,sample=sample,cache_sha256=hashlib.sha256(cache).hexdigest(),stats={p.name:p.read_text().strip() for p in Path('/sys/power/suspend_stats').iterdir() if p.is_file()},boottime=time.clock_gettime(time.CLOCK_BOOTTIME),monotonic=time.monotonic())
    assert not (out/'claim.json').exists();save('claim.json',dict(pid=os.getpid(),mem_write_limit=1))
    assert Path('/sys/power/mem_sleep').read_text().strip()=='[s2idle]'
    assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip()=='enabled'
    assert Path('/sys/class/power_supply/samurai-usb-input/power/wakeup').read_text().strip()=='enabled'
    assert json.loads(Path('/var/lib/samurai/gnss-assist/watch-state.json').read_bytes())['active'] is False
    before=snapshot();save('before.json',before)
    prior=subprocess.check_output(['dmesg']);(out/'dmesg-before.txt').write_bytes(prior)
    trace=PMScopedTrace(PMTraceFS(out.name));cleanup=None;result=dict(passed=False)
    try:
        trace.start()
        def phase(entry):
            with (out/'phases.jsonl').open('a') as stream:stream.write(json.dumps(entry)+'\n');stream.flush();os.fsync(stream.fileno())
        tx=suspend_once(SysfsPMIO(phase),alarm_delay_seconds=15,minimum_remaining_seconds=4,wakeup_count_timeout_seconds=10)
        save('transaction.json',tx);time.sleep(3)
        after=snapshot();save('after.json',after)
        log=subprocess.check_output(['dmesg']);(out/'dmesg-after.txt').write_bytes(log)
        assert log.startswith(prior);tail=log[len(prior):]
        faults={key:tail.count(key.encode()) for key in ['WARNING:','Oops:','refcount_t: underflow','gpu fault:','NGD resume failed','fatal error received','Unhandled context fault:','Kernel panic - not syncing']}
        delta={k:int(after['stats'][k])-int(v) for k,v in before['stats'].items() if v.isdigit() and after['stats'].get(k,'').isdigit()}
        residency=tx.get('estimated_residency_seconds',0)
        assert tx['outcome']=='returned' and tx['mem_write_attempts']==1 and tx['mem_returned'] and 10<=residency<=20
        assert delta.get('success')==1 and delta.get('fail',0)==0 and not any(faults.values())
        assert before['cache_sha256']==after['cache_sha256']
        result.update(passed=True,boot=before['boot'],RTC_residency_seconds=residency,suspend_stats_delta=delta,fault_delta=faults,
            native_budget_and_protection_recovered=True,cache_sha256=after['cache_sha256'],MAC_query_or_rearm=False,
            physical_USB_wakeup_verified=False,APSD_route_survives_PM=False,APSD_route_limit='normal PM pause/complete is installed; actual physical APSD transfer after PM remains untested')
    finally:
        cleanup=trace.close();result['trace_cleanup']=cleanup
        result['passed']=result['passed'] and not cleanup['cleanup_errors'];save('result.json',result)
    return 0 if result['passed'] else 1

if __name__=='__main__':
    try:
        ret=run_pm()
        with (Path(__file__).parent/'terminal.json').open('x') as stream:json.dump(dict(returncode=ret,pid=os.getpid()),stream)
        raise SystemExit(ret)
    except Exception:
        import traceback
        (Path(__file__).parent/'failure.txt').write_text(traceback.format_exc());raise
