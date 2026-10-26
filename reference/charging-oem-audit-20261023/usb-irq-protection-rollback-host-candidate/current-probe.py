"""Read-only actual #502 identity/full carriers/resident notes. Default is inert."""
from pathlib import Path
import hashlib,json,os,stat,struct,sys,time
OLD_NOTES = {'samurai-usb-input': 'f0edb792d30ee1168ee1793e89707aa48b2085c845acde8f472f2c13a03804b0', 'samurai-gauge-protection': '930e0e1f34e89e4e06a7632ca14a26181975f9f35e55a51209af71480b56fe76', 'samurai-mp2650': 'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'}
VERSION = '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'

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

class Probe:
    def __init__(self):
        self.carriers=None

    def identity(self):
        need(os.uname().version == VERSION and os.uname().release == RELEASE and os.uname().machine == 'aarch64', 'only exact current Image502')
        compatible = Path('/sys/firmware/devicetree/base/compatible').read_bytes()
        need(b'realme,samurai' in compatible.split(b'\0'), 'actual board compatible')
        return dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), version=os.uname().version,
            serial_sha256=sha(Path('/sys/devices/soc0/serial_number').read_bytes()), compatible_sha256=sha(compatible),
            rootfs_sha256=sha(read_owned('/etc/samurai-rootfs-release')[0]))

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


def main(request=None):
    if sys.flags.optimize:raise RuntimeError('nonoptimized Python required')
    if request is None:
        print(json.dumps(dict(source_only=True,device_accessed=False)));return 0
    need(request['schema']=='samurai-irq-rollback-current-probe-v1','bound current probe request')
    started=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    probe=Probe();before=probe.identity();current=probe.current(None);after=probe.identity()
    need(before==current['identity']==after,'identity changed during full current probe')
    print(json.dumps(dict(schema=request['schema'],request=request,identity_before=before,current=current,
        identity_after=after,started_boottime_ns=started,ended_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main(globals().get('PROBE_REQUEST')))
