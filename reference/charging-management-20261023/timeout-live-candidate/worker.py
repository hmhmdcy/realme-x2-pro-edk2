"""One explicitly bound formal506 timer observation; inert except as a CLI.

Requires a fresh private baseline and namespace. Never changes clock, limits,
modules, partitions, gauge commands or protection; uses normal AUTO once only
after a verified real timeout. A subsequent normal reboot recovers the volatile
period; this worker never clears an expired period or reboots by itself.
"""
from pathlib import Path
import fcntl,hashlib,importlib.util,json,os,re,runpy,signal,stat,subprocess,sys,time,traceback
HERE=Path(__file__).resolve().parent
shutdown_spec=importlib.util.spec_from_file_location('timer_shutdown_observer',HERE/'shutdown-observer.py')
shutdown=importlib.util.module_from_spec(shutdown_spec);shutdown_spec.loader.exec_module(shutdown)
SERVICE='/usr/sbin/samurai-charging'
SERVICE_SHA='83469a88beab16cd190793ddf65e672438d0a97aaa812b63a47b4bbb4f22472f'
MANIFEST='/usr/share/samurai-charging/manifest.json'
MANIFEST_SHA='8b402e1c37ca390ec2be4949738badb670e9b5c54cbcf6941c895935ed90bc0a'
NOTES={'samurai_mp2650':'1df00d554b85aa45d4bbbc0d1a6a7a4cbd56ba4da45ae48d54bb8ae1f3434d08',
 'samurai_usb_input':'3c6247f14ff9f2ab23c149de814a66980dcc6d91c03c396f0101cb56781ee0fa',
 'samurai_gauge_protection':'bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
text=lambda p:Path(p).read_text().strip()
CANCELLED=False
def cancel(signum,frame):
    global CANCELLED
    CANCELLED=True


class IO:
    def __init__(self):
        self.baseline=json.loads((HERE/'baseline-private.json').read_bytes())
        self.lock=None;self.manager=None;self.mac=None;self.mac_id=None;self.parts=[]
        self.load_closed=False;self.duty=0.03;self.ema=None
        self.deadline=self.now()+37000;self.last_attempt=None
    def now(self):return time.clock_gettime(time.CLOCK_BOOTTIME)
    def sleep(self,seconds):time.sleep(seconds)
    def save(self,name,value):
        target=HERE/name;temp=HERE/('.'+name+'.next')
        with temp.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        temp.replace(target)
    def attempt(self,phase,value):
        self.last_attempt=dict(phase=phase,value=value)
        self.save('attempt-private.json',self.last_attempt)
    def fail(self,stage,exc,value=None,partial=None,extra=None):
        payload=dict(stage=stage,type=type(exc).__name__,error=repr(exc),
            errno=getattr(exc,'errno',None),traceback=traceback.format_exc(),
            boottime=self.now(),realtime=time.time(),value=value,partial=partial,
            last_attempt=getattr(self,'last_attempt',None),extra=extra)
        try:payload['boot_id']=text('/proc/sys/kernel/random/boot_id')
        except BaseException as identity_error:
            payload['boot_id_error']=repr(identity_error)
        try:
            save=getattr(self,'save',None)
            if save:save('failure-private.json',payload)
        except BaseException as save_error:
            payload['save_error']=repr(save_error)
        return payload
    def identity(self):
        b=self.baseline
        assert os.geteuid()==0 and not sys.flags.optimize
        assert text('/proc/sys/kernel/random/boot_id')==b['boot_id']
        assert text(b['guard_path'])==b['boot_id']
        assert os.uname().version=='#506 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
        assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
        assert text('/proc/sys/kernel/tainted')=='4096'
        assert sha(SERVICE)==SERVICE_SHA and sha(MANIFEST)==MANIFEST_SHA
        for name,digest in NOTES.items():
            assert text('/sys/module/'+name+'/initstate')=='live'
            assert sha('/sys/module/'+name+'/notes/.note.gnu.build-id')==digest
        p=Path('/sys/devices/platform/samurai-gauge-protection');info=(p/'mac_evidence').stat()
        assert (info.st_dev,info.st_ino,p.stat().st_ino)==self.mac_id
        assert sha(p/'mac_evidence')==self.mac
    def setup(self):
        p=Path('/sys/devices/platform/samurai-gauge-protection');info=(p/'mac_evidence').stat()
        self.mac_id=(info.st_dev,info.st_ino,p.stat().st_ino);self.mac=sha(p/'mac_evidence');self.identity()
        self.lock=os.open('/run/lock/samurai-charging.lock',os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC)
        st=os.fstat(self.lock);assert stat.S_ISREG(st.st_mode) and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o600
        fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.manager=runpy.run_path(SERVICE)
        assert self.manager['live'].REGS==[0,1,2,3,4,5,7,8,9,15,19]
        self.meta=self.manager['verify']()
    def observe(self):
        out={}
        try:
            self.identity();start=self.now()
            out.update(boottime=self.now(),read_seconds=self.now()-start)
            out['sample']=self.manager['sample']()
            p=Path('/sys/class/power_supply')
            mode=text(p/'mp2650-input/charge_behaviour');selected=re.findall(r'\[([^\]]+)\]',mode)
            out['behaviour']=selected[0] if len(selected)==1 else mode
            regs=self.manager['live'].registers()
            out.update(register08=regs['08'],register13=regs['13'])
            out['protection']={k:int(v,0) for k,v in
                (x.split('=',1) for x in text('/sys/devices/platform/samurai-gauge-protection/protection_state').split())}
            out['source']={}
            for name in ['online','usb_type','current_max','input_current_limit']:
                out['source'][name]=text(p/'samurai-usb-input'/name)
            out['caps']={}
            for name in ['input_current_limit','constant_charge_current','constant_charge_voltage']:
                out['caps'][name]=int(text(p/'mp2650-input'/name))
            out['protection_health']=text(p/'samurai-gauge-protection/health')
            out['charger_health']=text(p/'mp2650-input/health')
            out['capacity']=int(text(p/'bq28z610-0/capacity'))
            out['current_avg_ua']=int(text(p/'bq28z610-0/current_avg'))
            self.identity();return out
        except BaseException as error:
            self.fail('observe',error,partial=out)
            raise
    def validate(self,value):
        try:
            failures=[]
            def check(name,ok,actual=None,expected=None):
                if not ok:failures.append(dict(name=name,actual=actual,expected=expected))
            s=value['sample'];p=value['protection'];source=value['source']
            now=self.now()
            check('timing',now<self.deadline and value['read_seconds']<=3 and now-value['boottime']<=1,
                dict(now=now,deadline=self.deadline,read_seconds=value['read_seconds'],
                     age=now-value['boottime']),'fresh before deadline')
            health={k:s.get(k) for k in ['shadow','valid','online','protection_ok','age_ms']}
            check('sample.health',health['shadow']==0 and
                health['valid']==health['online']==health['protection_ok']==1 and
                0<=health['age_ms']<=3000,health,
                dict(shadow=0,valid=1,online=1,protection_ok=1,age_ms='0..3000'))
            inhibited={k:s.get(k) for k in
                ['fault','stop_error','thermal_inhibit','source_inhibit','gauge_charge_stop']}
            check('sample.no_inhibit',all(v==0 for v in inhibited.values()),inhibited,
                {k:0 for k in inhibited})
            timing={k:s.get(k) for k in ['thermal_band','session_seconds']}
            check('charger.timer',timing['thermal_band']==4 and
                0<=timing['session_seconds']<=36000,timing,
                dict(thermal_band=4,session_seconds='0..36000'))
            check('protection.identity',value['protection_health']=='Good' and
                p['id']==0x2719 and p['safety']==p['pf']==p['error']==0,
                dict(health=value['protection_health'],id=p.get('id'),safety=p.get('safety'),
                     pf=p.get('pf'),error=p.get('error')),
                dict(health='Good',id=0x2719,safety=0,pf=0,error=0))
            check('protection.operation',p['operation']&0x300==0x300 and
                not p['operation']&((1<<20)|(1<<16)|0x7c00),hex(p['operation']),
                'required 0x300 bits; forbidden 0x119c00')
            check('protection.manufacturing',p['manufacturing']&0x18==0x18 and
                not p['manufacturing']&0x8006,hex(p['manufacturing']),
                'required 0x18 bits; forbidden 0x8006')
            check('source.usb',source['online']=='1' and '[SDP]' in source['usb_type'] and
                source['current_max']==source['input_current_limit']=='500000',
                source,dict(online='1',usb_type='SDP',current_max='500000',
                input_current_limit='500000'))
            check('charger.caps',value['caps']==dict(input_current_limit=500000,
                constant_charge_current=250000,constant_charge_voltage=8725000),
                value['caps'],dict(input_current_limit=500000,constant_charge_current=250000,
                constant_charge_voltage=8725000))
            check('gauge.capacity',10<=value['capacity']<=70,value['capacity'],'10..70')
            # Below20%, observe normal recharge only. Existing balance() clamps all
            # experimental CPU duty to zero through25%; do not wait for an extra boot.
            if value['capacity']<20 and not s['cycle_timeout']:
                low=dict(current_avg_ua=value.get('current_avg_ua'),
                    cell1_uv=s.get('cell1_uv'),cell2_uv=s.get('cell2_uv'))
                check('gauge.low_soc_recharge',low['current_avg_ua']>0 and
                    min(low['cell1_uv'],low['cell2_uv'])>=3700000,low,
                    dict(current_avg_ua='>0',each_cell_uv='>=3700000'))
            if s['cycle_timeout']:
                check('charger.timeout',s['error']==-62 and s['latched']==1,
                    dict(error=s.get('error'),latched=s.get('latched')),
                    dict(error=-62,latched=1))
            else:
                check('charger.healthy',not s['error'] and not s['latched'] and
                    value['charger_health']=='Good',
                    dict(error=s.get('error'),latched=s.get('latched'),
                         health=value.get('charger_health')),
                    dict(error=0,latched=0,health='Good'))
            if failures:
                names=','.join(row['name'] for row in failures)
                error=AssertionError('validation failed: '+names)
                self.fail('validate',error,value=value,extra=dict(failures=failures))
                error.stage='validate'
                raise error
        except AssertionError:
            raise
        except BaseException as error:
            self.fail('validate',error,value=value)
            raise
    def record(self,phase,value):
        row=dict(phase=phase,boottime=self.now(),value=value)
        with (HERE/'samples-private.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n');stream.flush();os.fsync(stream.fileno())
        self.save('status-private.json',row)
        self.save('heartbeat.json',dict(boottime=self.now(),pid=os.getpid()))
    def cancelled(self):
        if CANCELLED or (HERE/'cancel').exists():return True
        event=shutdown.pending_openrc_shutdown()
        if event is None:return False
        self.save('shutdown-observed.json',dict(boottime=self.now(),**event))
        return True
    def balance(self,value):
        assert not self.load_closed
        s=value['sample'];current=s['gauge_current_ua'];soc=value['capacity']
        self.ema=current if self.ema is None else self.ema*0.8+current*0.2
        target=10000 if soc<35 else -10000 if soc>55 else 0
        self.duty=max(0.,min(0.3,self.duty+max(-0.01,min(0.01,(self.ema-target)/5000000))))
        if s['temp_decic']>=340:self.duty=min(self.duty,0.1)
        if s['temp_decic']>=350 or min(s['cell1_uv'],s['cell2_uv'])<=3600000 or soc<=25:self.duty=0.
        self.save('cpu-load-control.json',dict(duty=self.duty,boottime=self.now(),current_ema_ua=self.ema,target_ua=target))
        if not self.parts:
            assert {4,7}.issubset(os.sched_getaffinity(0));rows=[]
            try:
                for cpu in (4,7):
                    with (HERE/('cpu'+str(cpu)+'.stderr')).open('xb') as err:
                        p=subprocess.Popen([sys.executable,'-B',str(HERE/'cpu-load.py'),str(cpu),str(os.getpid()),str(self.deadline)],
                            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err,close_fds=True)
                    self.parts.append(p);f=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()
                    rows.append(dict(pid=p.pid,startticks=int(f[19]),cpu=cpu))
                self.save('cpu-load-launch.json',dict(parent=os.getpid(),parts=rows,maximum_duty=0.3))
            except BaseException:self.stop_load();raise
        dead=[]
        for p in self.parts:
            returncode=p.poll()
            if returncode is not None:
                dead.append(dict(pid=p.pid,returncode=returncode,
                    argv=getattr(p,'args',None)))
        if dead:
            error=RuntimeError('owned load exited early')
            self.fail('balance.helper_exit',error,value=value,extra=dict(dead=dead))
            error.stage='balance'
            raise error
    def stop_load(self):
        if self.load_closed:return
        rows=[]
        for p in self.parts:
            if p.poll() is None:p.terminate()
        for p in self.parts:
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:p.kill();p.wait()
            rows.append(dict(pid=p.pid,returncode=p.returncode,joined=True))
        self.load_closed=True
        if self.parts:self.save('cpu-load-terminal.json',dict(parts=rows,all_joined=True))
    def request_auto(self):
        self.identity();v=self.observe();self.validate(v)
        assert v['sample']['cycle_timeout']==1 and v['sample']['session_seconds']==36000
        assert v['sample']['error']==-62 and v['register08']&0x18==8
        assert self.manager['verify']()==self.meta
        self.save('AUTO-after-timeout-request.json',dict(boottime=self.now(),before=v))
        # Existing kernel operator interface; never use the service's healthy-
        # resume command for an intentionally expired period.
        Path('/sys/class/power_supply/mp2650-input/charge_behaviour').write_text('auto\n')
    def close(self):
        try:self.stop_load()
        finally:
            if self.lock is not None:os.close(self.lock);self.lock=None


def main():
    assert sys.argv[1:] in [['--preflight'],['--execute']]
    assert not (HERE/'result-private.json').exists()
    io=IO()
    try:
        io.setup();before=io.observe();io.validate(before)
        assert before['behaviour']=='auto' and before['sample']['desired_enable']==1
        assert before['sample']['cycle_timeout']==0 and 0<=before['sample']['session_seconds']<=900
        assert before['sample']['logical_full']==0 and before['sample']['full_cause']==0
        if sys.argv[1:]==['--preflight']:
            print(json.dumps(dict(passed=True,read_only=True,before=before)));return 0
        signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
        spec=importlib.util.spec_from_file_location('bounded_real_timer',HERE/'exercise.py')
        e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
        result=e.observe_timeout(io);io.save('result-private.json',result)
        rc=0 if result['error'] is None and result['cleanup_error'] is None else 1
        io.save('worker-terminal.json',dict(pid=os.getpid(),returncode=rc,observation_passed=result['passed']))
        return rc
    finally:io.close()
if __name__=='__main__':raise SystemExit(main())
