class PMTraceFS:
    def __init__(self, name):
        assert name=='pm504-wakeup-live-20261024-03'
        self.root=Path('/sys/kernel/tracing/instances')/name
        self.out=Path(__file__).resolve().parent
    def mkdir(self):self.root.mkdir()
    def read(self,name):return (self.root/name).read_text()
    def write(self,name,value):
        assert name in ['tracing_on','trace_clock','buffer_size_kb',
                        'events/power/wakeup_source_activate/filter','events/power/wakeup_source_activate/trigger',
                        'events/power/wakeup_source_activate/enable','events/power/suspend_resume/enable']
        (self.root/name).write_text(value)
    def stats(self):
        return {p.parent.name:p.read_text() for p in sorted((self.root/'per_cpu').glob('cpu*/stats'))}
    def remove(self):self.root.rmdir()
    def save(self,name,value):
        assert name in ['trace-capabilities-private.json','trace-config-private.json','trace-cleanup-private.json']
        with (self.out/name).open('x') as file:
            json.dump(value,file,indent=2);file.write('\n');file.flush();os.fsync(file.fileno())
    def save_trace(self):
        raw=(self.root/'trace').read_bytes();assert len(raw)<=4*1024*1024
        with (self.out/'pm-wakeup-trace-private.txt').open('xb') as file:
            file.write(raw);file.flush();os.fsync(file.fileno())
        return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),per_cpu=self.stats())

class PMScopedTrace:
    FILTER='name == "samurai-usb-input" || name == "mp2650-input" || name == "samurai-gauge-protection"'
    TRIGGER='stacktrace:8 if name == "samurai-usb-input"'
    def __init__(self,io):
        self.io=io;self.created=False;self.trigger=False;self.enabled=[];self.config={}
    def start(self):
        self.io.mkdir();self.created=True
        self.io.write('tracing_on','0')
        capability={name:self.io.read('events/power/'+name+'/format') for name in ['wakeup_source_activate','suspend_resume']}
        capability['trigger']=self.io.read('events/power/wakeup_source_activate/trigger')
        capability['clock']=self.io.read('trace_clock')
        self.io.save('trace-capabilities-private.json',capability)
        assert 'field:__data_loc char[] name;' in capability['wakeup_source_activate']
        assert 'field:u64 state;' in capability['wakeup_source_activate']
        assert 'field:const char * action;' in capability['suspend_resume'] and 'field:bool start;' in capability['suspend_resume']
        assert 'stacktrace' in capability['trigger'] and 'boot' in capability['clock'].replace('[','').replace(']','').split()
        self.io.write('buffer_size_kb','128')
        self.io.write('trace_clock','boot');assert '[boot]' in self.io.read('trace_clock')
        self.io.write('events/power/wakeup_source_activate/filter',self.FILTER)
        observed=self.io.read('events/power/wakeup_source_activate/filter')
        assert observed.strip()==self.FILTER
        self.io.write('events/power/wakeup_source_activate/trigger',self.TRIGGER);self.trigger=True
        trigger=self.io.read('events/power/wakeup_source_activate/trigger')
        assert 'stacktrace' in trigger and 'samurai-usb-input' in trigger
        enabled_readbacks={}
        for name in ['wakeup_source_activate','suspend_resume']:
            self.io.write('events/power/'+name+'/enable','1');self.enabled.append(name)
            enabled_readbacks[name]=self.io.read('events/power/'+name+'/enable').strip()
            # The kernel appends * for conditional-trigger soft mode. 0* is
            # still disabled; 1* is an enabled event with that extra reference.
            assert enabled_readbacks[name] in ['1','1*']
        self.config=dict(filter=observed,trigger=trigger,clock=self.io.read('trace_clock'),
                         boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME),monotonic_ns=time.monotonic_ns(),
                         buffer_kb_per_cpu=128,stack_trigger_limit=8,events=list(self.enabled),enable_readbacks=enabled_readbacks)
        self.io.save('trace-config-private.json',self.config)
        self.io.write('tracing_on','1');assert self.io.read('tracing_on').strip()=='1'
    def close(self):
        errors=[];evidence=None
        def attempt(label,fn):
            try:return fn()
            except BaseException as error:errors.append(dict(phase=label,error=repr(error)))
        if self.created:
            attempt('tracing_off',lambda:self.io.write('tracing_on','0'))
            evidence=attempt('retain_trace',self.io.save_trace)
            for name in self.enabled:
                attempt('disable_'+name,lambda name=name:self.io.write('events/power/'+name+'/enable','0'))
            if self.trigger:attempt('remove_own_stack_trigger',lambda:self.io.write('events/power/wakeup_source_activate/trigger','!stacktrace'))
            attempt('clear_own_filter',lambda:self.io.write('events/power/wakeup_source_activate/filter','0'))
            attempt('remove_own_instance',self.io.remove)
        result=dict(created=self.created,evidence=evidence,cleanup_errors=errors,
                    global_trace_modified=False,wakeup_policy_modified=False,
                    boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME),monotonic_ns=time.monotonic_ns())
        self.io.save('trace-cleanup-private.json',result)
        return result

def pm_smoke():
    request=PM_REQUEST['postboot_request'];validate_request(request)
    assert Path(PM_REQUEST['adoption_guard']).read_text()==request['new_boot_id']+'\n'
    check_identity(identity(),request['guard'])
    assert Path('/sys/class/power_supply/samurai-usb-input/power/wakeup').read_text().strip()=='enabled'
    trace=PMScopedTrace(PMTraceFS(Path(__file__).resolve().parent.name));primary=None
    try:
        trace.start()
        return pm_smoke_base()
    except BaseException as error:
        primary=error;raise
    finally:
        try:
            cleanup=trace.close()
            if cleanup['cleanup_errors'] and primary is None:raise RuntimeError('owned trace cleanup incomplete')
        except BaseException:
            if primary is None:raise
