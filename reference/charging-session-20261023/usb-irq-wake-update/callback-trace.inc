class IRQWakeTraceFS(PMTraceFS):
    EXTRA = {'events/power/'+event+'/'+field for event in
             ('device_pm_callback_start','device_pm_callback_end') for field in ('filter','enable')}
    def write(self,name,value):
        if name in self.EXTRA:
            (self.root/name).write_text(value)
        else:
            super().write(name,value)
    def extra_save(self,name,value):
        assert name in ('usb-callback-config-private.json','usb-callback-cleanup-private.json')
        with (self.out/name).open('x') as file:
            json.dump(value,file,indent=2);file.write('\n');file.flush();os.fsync(file.fileno())

class IRQWakeScopedTrace(PMScopedTrace):
    def __init__(self,io):
        super().__init__(io);self.callback_filters=[]
    def start(self):
        super().start()
        self.io.write('tracing_on','0')
        capability={event:self.io.read('events/power/'+event+'/format') for event in
                    ('device_pm_callback_start','device_pm_callback_end')}
        assert all('field:__data_loc char[] driver;' in value for value in capability.values())
        assert 'field:int error;' in capability['device_pm_callback_end']
        readbacks={};filt='driver == "samurai-usb-input"'
        for event in capability:
            name='events/power/'+event+'/filter';self.callback_filters.append(name)
            self.io.write(name,filt);assert self.io.read(name).strip()==filt
            self.enabled.append(event)
            self.io.write('events/power/'+event+'/enable','1')
            readbacks[event]=self.io.read('events/power/'+event+'/enable').strip()
            assert readbacks[event]=='1'
        self.io.extra_save('usb-callback-config-private.json',dict(formats=capability,filter=filt,enable_readbacks=readbacks))
        self.io.write('tracing_on','1')
    def close(self):
        errors=[]
        if self.created:
            try:self.io.write('tracing_on','0')
            except BaseException as error:errors.append(dict(phase='extra_tracing_off',error=repr(error)))
            for name in self.callback_filters:
                try:self.io.write(name,'0')
                except BaseException as error:errors.append(dict(phase=name,error=repr(error)))
        result=super().close()
        self.io.extra_save('usb-callback-cleanup-private.json',dict(cleanup_errors=errors,owned_instance_only=True))
        result['cleanup_errors']+=errors
        return result

PMTraceFS=IRQWakeTraceFS
PMScopedTrace=IRQWakeScopedTrace
