"""Read-only current kernel/carriers/notes/cache. Default does not access a device."""
from pathlib import Path
import base64,hashlib,json,os,re,stat,struct,sys,time
sys.dont_write_bytecode=True
OLD_NOTES={'samurai-usb-input': 'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d', 'samurai-gauge-protection': 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec', 'samurai-mp2650': 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
NEW_NOTES={'samurai-usb-input': '08523f9f969b00a278a87ddd5d27ec3b54ac9b53a9c84f6429c4ecf5934c0f3f', 'samurai-gauge-protection': 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec', 'samurai-mp2650': 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
VERSION502='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
VERSION504='#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
BOOT='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
LOGDUMP502='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
LOGDUMP504='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83'
INSTANCE='/sys/devices/platform/samurai-gauge-protection'
PROFILES=('staged_same_boot_old_resident', 'booted_504_new_resident', 'booted_502_new_resident')

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read_owned(path, limit=4_000_000):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
             'regular root-owned protected file: ' + str(path))
        need(0 <= info.st_size <= limit, 'bounded regular file: ' + str(path))
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        need(len(raw) <= limit, 'growing file bound')
        return raw, stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)

def expected_profile(request):
 index=PROFILES.index(request['profile'])
 return {'version':VERSION504 if index==1 else VERSION502,'boot':BOOT,
  'logdump':LOGDUMP504 if index==1 else LOGDUMP502,'notes':OLD_NOTES if index==0 else NEW_NOTES}

def validate_cache(value):
 need(isinstance(value,dict) and set(value)=={'sha256','raw_base64','attribute_dev','attribute_inode','instance_inode'},'actual current cache fields')
 raw=base64.b64decode(value['raw_base64'],validate=True)
 need(0<len(raw)<16384 and raw.endswith(b'\n') and re.fullmatch('[0-9a-f]{64}',value['sha256']) and
  sha(raw)==value['sha256'],'exact current opaque cache bytes')
 first=dict(x.split('=',1) for x in raw.decode().splitlines()[0].split())
 need(first.get('schema')=='1' and (first.get('attempted'),first.get('terminal')) in [('0','0'),('1','1')],
  'fixed7848 cache must be untouched or already terminal; no capture in progress')
 need(type(value['attribute_dev']) is int and value['attribute_dev']>=0 and
  all(type(value[k]) is int and value[k]>0 for k in ['attribute_inode','instance_inode']),'current kernfs instance identity')
 return raw

class ProbeIdentity:
 def identity(self):
  need(self.request is not None,'explicit current request')
  need(os.uname().version==expected_profile(self.request)['version'] and os.uname().release==RELEASE and
   os.uname().machine=='aarch64','exact current profile kernel')
  compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
  need(b'realme,samurai' in compatible.split(b'\0'),'actual board')
  return dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),version=os.uname().version,
   serial_sha256=sha(Path('/sys/devices/soc0/serial_number').read_bytes()),compatible_sha256=sha(compatible),
   rootfs_sha256=sha(read_owned('/etc/samurai-rootfs-release')[0]))
 def cache_evidence(self):
  need(self.mac_fd is not None,'held current cache fd')
  p=Path(INSTANCE);held,current=os.fstat(self.mac_fd),(p/'mac_evidence').stat()
  need((held.st_dev,held.st_ino)==(current.st_dev,current.st_ino) and
   (p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','same bound current cache fd')
  os.lseek(self.mac_fd,0,os.SEEK_SET);raw=os.read(self.mac_fd,16384)
  value=dict(sha256=sha(raw),raw_base64=base64.b64encode(raw).decode(),attribute_dev=held.st_dev,
   attribute_inode=held.st_ino,instance_inode=p.stat().st_ino)
  validate_cache(value);need(self.baseline is None or value==self.baseline,'same current cache throughout read-only bracket')
  return value

class ProbeCarriers:
    def block_fact(self, name, length):
        import fcntl
        fd=os.open('/dev/disk/by-partlabel/'+name,os.O_RDONLY|os.O_CLOEXEC)
        try:
            need(stat.S_ISBLK(os.fstat(fd).st_mode) and struct.unpack('=Q',fcntl.ioctl(fd,0x80081272,bytes(8)))[0]==length,'complete read-only carrier')
            digest=hashlib.sha256(); remaining=length
            while remaining:
                raw=os.read(fd,min(1048576,remaining));need(raw,'short carrier');digest.update(raw);remaining-=len(raw)
            return dict(bytes=length,sha256=digest.hexdigest())
        finally: os.close(fd)
    def current(self, request, carriers=True):
        if carriers: self.carriers={name:self.block_fact(name,length) for name,length in [('boot',100663296),('logdump',67108864)]}
        need(self.carriers is not None,'initial complete carrier read required')
        notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES}
        return dict(identity=self.identity(),release=os.uname().release,machine=os.uname().machine,
            taint=Path('/proc/sys/kernel/tainted').read_text().strip(),notes=notes,
            module_states={name:Path('/sys/module',name.replace('-','_'),'initstate').read_text().strip() for name in notes},**self.carriers)

class Probe(ProbeIdentity,ProbeCarriers):
    def __init__(self,request):
        self.request=request;self.carriers=None;self.mac_fd=None;self.baseline=None
    def open_cache(self):
        p=Path(INSTANCE)
        need((p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','current protection driver')
        self.mac_fd=os.open(p/'mac_evidence',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        self.baseline=self.cache_evidence()
    def close(self):
        if self.mac_fd is not None:
            try:os.close(self.mac_fd)
            finally:self.mac_fd=None

def collect(request,probe):
    need(request['schema']=='samurai-irq-native-usb-pm-rollback-current-probe-v1','current probe schema')
    start=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    try:
        before=probe.identity();probe.open_cache();cache_before=probe.cache_evidence()
        current=probe.current(request);current['current_cache']=probe.cache_evidence()
        after=probe.identity();cache_after=probe.cache_evidence()
        need(before==current['identity']==after and cache_before==current['current_cache']==cache_after,'current identity/cache bracket')
        return dict(schema=request['schema'],request=request,identity_before=before,current=current,identity_after=after,
            cache_before=cache_before,cache_after=cache_after,started_boottime_ns=start,
            ended_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))
    finally:probe.close()

def main(request=None):
    if sys.flags.optimize:raise RuntimeError('non-optimized Python required')
    if request is None:print(json.dumps({'source_only':True,'device_accessed':False}));return 0
    need(set(request)=={'schema','new_endpoint','profile','saved_source_binding_sha256'} and request['profile'] in PROFILES,
        'explicit source-bound current probe')
    print(json.dumps(collect(request,Probe(request))),flush=True);return 0
if __name__=='__main__':raise SystemExit(main(globals().get('PROBE_REQUEST')))
