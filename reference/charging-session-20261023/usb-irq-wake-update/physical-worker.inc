def physical_test():
    out=Path(__file__).resolve().parent
    request=PM_REQUEST['postboot_request']
    def save(name,value):
        with (out/name).open('x') as f:
            json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    def snapshot(name):
        raw={};collect(request,raw);result=audit(raw,request)
        save(name,dict(raw=raw,result=result))
        assert result['passed'] and len(result['checks'])==12 and not result['errors']
        return raw
    def stats():
        return {p.name:int(p.read_text()) for p in Path('/sys/power/suspend_stats').iterdir()
                if p.is_file() and p.read_text().strip().isdigit()}
    def interrupts():
        text=Path('/proc/interrupts').read_text();rows={}
        for line in text.splitlines():
            if ':' not in line:continue
            key,tail=line.split(':',1)
            if not key.strip().isdigit():continue
            fields=tail.split();counts=[]
            for field in fields:
                if not field.isdigit():break
                counts.append(int(field))
            if counts:rows[int(key)]=dict(count=sum(counts),text=line)
        return dict(text=text,rows=rows)
    def supply():
        result=dict(boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))
        for name in ['online','input_current_limit']:
            try:result[name]=(Path('/sys/class/power_supply/samurai-usb-input')/name).read_text().strip()
            except OSError as error:result[name]=dict(errno=error.errno)
        return result
    def phase(value):
        with (out/'phases-private.jsonl').open('a') as f:
            f.write(json.dumps(value)+'\n');f.flush();os.fsync(f.fileno())
    check_identity(identity(),request['guard'])
    assert Path(PM_REQUEST['adoption_guard']).read_text()==request['new_boot_id']+'\n'
    assert Path('/sys/power/mem_sleep').read_text().strip()=='[s2idle]'
    assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip()=='enabled'
    assert Path('/sys/class/power_supply/samurai-usb-input/power/wakeup').read_text().strip()=='enabled'
    assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
    assert json.loads(Path('/var/lib/samurai/gnss-assist/watch-state.json').read_bytes())['active'] is False
    snapshot('before-private.json')
    irq_before=interrupts();native={}
    for name in ['usbin-plugin','usbin-src-change']:
        matches=[irq for irq,row in irq_before['rows'].items() if row['text'].endswith(name)]
        assert len(matches)==1
        native[name]=matches[0]
    save('ready-private.json',dict(boot_id=request['new_boot_id'],native_irqs=native,monotonic=time.monotonic()))
    deadline=time.monotonic()+240
    while not (out/'go-private.json').exists():
        if time.monotonic()>deadline:
            save('expired-private.json',dict(PM_requested=False));return 2
        time.sleep(.2)
    go=json.loads((out/'go-private.json').read_bytes())
    assert go['boot_id']==request['new_boot_id'] and 0<=time.monotonic()-go['monotonic']<10
    # Give the host time to deliver the human's prompt. No alarm exists here.
    time.sleep(12)
    check_identity(identity(),request['guard'])
    save('mem-once-claim-private.json',dict(boot_id=request['new_boot_id'],mem_write_limit=1))
    first=stats();irq_before=interrupts();log_before=subprocess.check_output(['dmesg'])
    save('irq-before-private.json',irq_before);save('stats-before-private.json',first)
    (out/'dmesg-before-private.txt').write_bytes(log_before)
    io=SysfsPMIO(phase);rtc_before=io.read_rtc_irq()
    trace=PhysicalScopedTrace(PhysicalTraceFS(out.name),set(native.values()))
    cleanup=None
    try:
        trace.start()
        transaction=suspend_once(io,alarm_delay_seconds=60,minimum_remaining_seconds=45,wakeup_count_timeout_seconds=10)
        # Capture cause and line state immediately on return, before reconnect.
        wake=Path('/sys/power/pm_wakeup_irq')
        early=dict(pm_wakeup_irq=wake.read_text().strip() if wake.exists() else None,
                   rtc_irq_delta=io.read_rtc_irq()-rtc_before,rtc_epoch=io.read_rtc_epoch(),
                   source=supply(),interrupts=interrupts())
        save('pm-transaction-private.json',transaction);save('wake-immediate-private.json',early)
    finally:
        cleanup=trace.close()
    # Observe the genuine disconnect/reconnect without polling the raw bus.
    deadline=time.monotonic()+90;observations=[];stable=0
    while time.monotonic()<deadline:
        sample=supply();observations.append(sample)
        stable=stable+1 if sample.get('online')=='1' and sample.get('input_current_limit')=='500000' else 0
        if stable>=10:break
        time.sleep(.2)
    save('source-recovery-private.json',observations)
    snapshot('after-private.json')
    last=stats();irq_after=interrupts();log_after=subprocess.check_output(['dmesg'])
    save('irq-after-private.json',irq_after);save('stats-after-private.json',last)
    (out/'dmesg-after-private.txt').write_bytes(log_after)
    delta={key:last[key]-value for key,value in first.items() if key in last}
    tail=log_after[len(log_before):] if log_after.startswith(log_before) else b''
    faults={key:tail.count(key.encode()) for key in ['WARNING:','Oops:','refcount_t: underflow','gpu fault:',
            'NGD resume failed','fatal error received','Unhandled context fault:','Kernel panic - not syncing']}
    residency=transaction.get('estimated_residency_seconds',0)
    functional=bool(transaction['outcome']=='returned' and transaction['mem_write_attempts']==1
                    and transaction['mem_returned'] and delta.get('success')==1 and delta.get('fail',0)==0
                    and log_after.startswith(log_before) and not any(faults.values())
                    and stable>=10 and not cleanup['cleanup_errors'])
    save('result-private.json',dict(terminal=True,functional_passed=functional,transaction=transaction,
         native_irqs=native,suspend_stats_delta=delta,fault_delta=faults,
         USB_early_wake_candidate=bool(functional and 1<=residency<55 and early['rtc_irq_delta']==0),
         physical_wakeup_accepted=False,reason='Host must correlate retained IRQ trace, real edge and wake cause'))
    return 0 if functional else 1


class PhysicalTraceFS(IRQWakeTraceFS):
    EXTRA=IRQWakeTraceFS.EXTRA|{'events/irq/irq_handler_entry/'+field for field in ['filter','enable']}


class PhysicalScopedTrace(IRQWakeScopedTrace):
    def __init__(self,io,irqs):
        super().__init__(io);self.irqs=irqs;self.irq_filter=False;self.irq_enabled=False
    def start(self):
        super().start();self.io.write('tracing_on','0')
        fmt=self.io.read('events/irq/irq_handler_entry/format');assert 'field:int irq;' in fmt
        filt=' || '.join('irq == '+str(irq) for irq in sorted(self.irqs))
        self.irq_filter=True;self.io.write('events/irq/irq_handler_entry/filter',filt)
        assert self.io.read('events/irq/irq_handler_entry/filter').strip()==filt
        self.irq_enabled=True;self.io.write('events/irq/irq_handler_entry/enable','1')
        assert self.io.read('events/irq/irq_handler_entry/enable').strip()=='1'
        with (self.io.out/'physical-trace-config-private.json').open('x') as f:
            json.dump(dict(format=fmt,filter=filt,IRQs=sorted(self.irqs)),f);f.flush();os.fsync(f.fileno())
        self.io.write('tracing_on','1')
    def close(self):
        errors=[]
        if self.created:
            for name,value in [('tracing_on','0')]+([('events/irq/irq_handler_entry/enable','0')] if self.irq_enabled else [])+([('events/irq/irq_handler_entry/filter','0')] if self.irq_filter else []):
                try:self.io.write(name,value)
                except BaseException as error:errors.append(dict(phase=name,error=repr(error)))
        result=super().close();result['cleanup_errors']+=errors
        with (self.io.out/'physical-trace-cleanup-private.json').open('x') as f:
            json.dump(dict(cleanup_errors=errors,own_instance_only=True),f);f.flush();os.fsync(f.fileno())
        return result


if __name__=='__main__':
    try:raise SystemExit(physical_test())
    except Exception:
        import traceback
        (Path(__file__).resolve().parent/'failure-private.txt').write_text(traceback.format_exc())
        raise
