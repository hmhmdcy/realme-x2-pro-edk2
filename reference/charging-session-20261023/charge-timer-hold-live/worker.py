"""One current-boot confirmed-stop observation. Only original stop/resume."""
from pathlib import Path
import fcntl,hashlib,importlib.util,json,os,re,runpy,stat,sys,time
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('bounded_timer_exercise',HERE/'exercise.py');e=importlib.util.module_from_spec(s);s.loader.exec_module(e)
BOOT='bc612fca-e609-4c65-8afb-3682b3645793'
MANIFEST='/usr/share/samurai-charging/manifest.json';MANIFEST_SHA='f15ecc205d42e42f54b53f0052c8ebb4b011bc395756848a59373ce283d46bb5'
SERVICE='/usr/sbin/samurai-charging';SERVICE_SHA='83469a88beab16cd190793ddf65e672438d0a97aaa812b63a47b4bbb4f22472f'
GUARD='/var/lib/samurai/irq-native-usb-pm-activate-timer-20261024-01-adopted/boot-id-private.txt'
NOTES={'samurai_mp2650':'1df00d554b85aa45d4bbbc0d1a6a7a4cbd56ba4da45ae48d54bb8ae1f3434d08',
       'samurai_usb_input':'028ea63c24b0b46ec6edb03b9c3cbfc999c4b7a119034dc18ac70d1bcbf064e6',
       'samurai_gauge_protection':'bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd'}
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def text(path):return Path(path).read_text().strip()
class IO:
    def __init__(self, runtime_limit=115):
        assert type(runtime_limit) is int and 115<=runtime_limit<=5720
        self.manager=None;self.mac=None;self.mac_id=None;self.lock=None;self.commands=[];self.started=self.now();self.runtime_limit=runtime_limit
    def now(self):return time.clock_gettime(time.CLOCK_BOOTTIME)
    def sleep(self,value):time.sleep(value)
    def identity(self):
        assert os.geteuid()==0 and not sys.flags.optimize and text('/proc/sys/kernel/random/boot_id')==BOOT
        assert os.uname().version=='#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026' and text('/proc/sys/kernel/tainted')=='0'
        assert text(GUARD)==BOOT and sha(Path(MANIFEST).read_bytes())==MANIFEST_SHA and sha(Path(SERVICE).read_bytes())==SERVICE_SHA
        assert (Path('/sys/bus/i2c/devices/0-005c')/'driver').resolve().name=='samurai-mp2650'
        for name,digest in NOTES.items():
            assert text('/sys/module/'+name+'/initstate')=='live' and sha(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes())==digest
        p=Path('/sys/devices/platform/samurai-gauge-protection');info=(p/'mac_evidence').stat()
        assert (info.st_dev,info.st_ino,p.stat().st_ino)==self.mac_id
        assert sha((p/'mac_evidence').read_bytes())==self.mac
    def observe(self):
        self.identity();p=Path('/sys/class/power_supply');start=self.now();sample=self.manager['sample']()
        behaviour=text(p/'mp2650-input/charge_behaviour');active=re.findall(r'\[([^\]]+)\]',behaviour)
        protection={k:int(v,0) for k,v in (word.split('=',1) for word in text('/sys/devices/platform/samurai-gauge-protection/protection_state').split())}
        # Same fixed existing register reader; excludes destructive REG14.
        register08=self.manager['live'].registers()['08']
        value=dict(boottime=self.now(),read_seconds=self.now()-start,sample=sample,behaviour=active[0] if len(active)==1 else behaviour,register08=register08,
            source={key:text(p/'samurai-usb-input'/key) for key in ['online','usb_type','current_max','input_current_limit']},
            caps={key:int(text(p/'mp2650-input'/key)) for key in ['input_current_limit','constant_charge_current','constant_charge_voltage']},
            protection=protection,health=text(p/'samurai-gauge-protection/health'))
        self.identity();return value
    def validate(self,value):
        s=value['sample'];source=value['source'];protection=value['protection']
        assert self.now()-self.started<self.runtime_limit and value['read_seconds']<=3 and self.now()-value['boottime']<=1
        assert s['shadow']==0 and s['valid']==s['online']==s['protection_ok']==1 and 0<=s['age_ms']<=3000
        assert not any(s[k] for k in ['fault','error','stop_error','latched','cycle_timeout','source_inhibit','thermal_inhibit','gauge_charge_stop'])
        assert 160<=s['temp_decic']<440 and s['thermal_band']==4 and 0<=s['session_seconds']<36000
        assert all(2000000<=s[k]<=4600000 for k in ['cell1_uv','cell2_uv']) and abs(s['cell1_uv']+s['cell2_uv']-s['pack_uv'])<=200000
        assert source['online']=='1' and '[SDP]' in source['usb_type'] and source['current_max']==source['input_current_limit']=='500000'
        assert value['caps']==dict(input_current_limit=500000,constant_charge_current=250000,constant_charge_voltage=8725000)
        assert value['health']=='Good' and protection['id']==0x2719 and protection['safety']==protection['pf']==protection['error']==0
        assert protection['operation']&0x300==0x300 and not protection['operation']&((1<<20)|(1<<16)|0x7c00)
        assert protection['manufacturing']&0x18==0x18 and not protection['manufacturing']&0x8006
    def command(self,action):
        assert action in ['stop','resume'];self.identity()
        assert self.manager['verify']()==self.meta
        self.commands.append(dict(action=action,boottime=self.now()));self.save('commands-private.json',self.commands)
        result=self.manager['command'](self.meta,action)
        assert result['managed'] and result['requested']==('inhibit-charge' if action=='stop' else 'auto')
    def save(self,name,value):
        temporary=HERE/('.'+name+'.next');target=HERE/name
        with temporary.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        temporary.replace(target)
    def setup(self):
        p=Path('/sys/devices/platform/samurai-gauge-protection');info=(p/'mac_evidence').stat()
        self.mac_id=(info.st_dev,info.st_ino,p.stat().st_ino);self.mac=sha((p/'mac_evidence').read_bytes());self.identity()
        self.lock=os.open('/run/lock/samurai-charging.lock',os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC)
        info=os.fstat(self.lock);assert stat.S_ISREG(info.st_mode) and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o600
        fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.manager=runpy.run_path(SERVICE);assert self.manager['live'].REGS==[0,1,2,3,4,5,7,8,9,15,19]
        self.meta=self.manager['verify']();assert sha(Path(SERVICE).read_bytes())==SERVICE_SHA
        assert not text('/sys/class/rtc/rtc0/wakealarm')
    def close(self):
        if self.lock is not None:os.close(self.lock);self.lock=None
def main():
    io=IO();result=None
    try:
        io.setup();result=e.exercise(io,60);io.save('result-private.json',result)
    except BaseException as error:
        io.save('failure-private.json',dict(error=repr(error),commands=io.commands));raise
    finally:io.close()
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
