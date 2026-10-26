# Embedded verbatim into both workers by prepare.py; no device action on import.
import fcntl,hashlib,re,stat,struct,sys

EUD_BOOT_SCHEMA='samurai-image501-activation-v1'
CANDIDATE_BOOT='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
ROLLBACK_BOOT='4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'
CANDIDATE_LOGDUMP='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'
IMAGE501='3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'
STARTUP500='2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a'
IMAGE363='15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'
LOGDUMP365='aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da'
CAMERA481='1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
CAMERA_RETURN='071c5353bac3f25b97c61ea897853f69c0eaff659771043263a2641f1c8fb8e8'
R8_MANIFEST='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
R8_NOTES={'samurai_usb_input':'f0edb792d30ee1168ee1793e89707aa48b2085c845acde8f472f2c13a03804b0',
 'samurai_gauge_protection':'930e0e1f34e89e4e06a7632ca14a26181975f9f35e55a51209af71480b56fe76',
 'samurai_mp2650':'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'}
SENSOR468_NOTE='a52ef87a2388757c542768e5438120d858e785bd334c080b55dec0f532c54d13'
OLD_BOOT_GUARD='/var/lib/samurai/eud-boot-r2-live-001-adopted/boot-id-private.txt'

def secure_file(path):
 p=Path(path);assert p.is_file() and not p.is_symlink(),str(p)
 s=p.stat();assert s.st_uid==0 and not s.st_mode&0o022,str(p)
 return p

def file_sha(path):
 return hashlib.sha256(secure_file(path).read_bytes()).hexdigest()

def block_sha(path,expected_bytes):
 # This is the existing read-only by-partlabel boundary, with an actual block
 # size check. Never read a writable mapping or use blockdev's mutation paths.
 fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC)
 try:
  assert stat.S_ISBLK(os.fstat(fd).st_mode)
  assert struct.unpack('=Q',fcntl.ioctl(fd,0x80081272,bytes(8)))[0]==expected_bytes
  digest=hashlib.sha256();remaining=expected_bytes
  while remaining:
   data=os.read(fd,min(1048576,remaining));assert data,'short partition read'
   digest.update(data);remaining-=len(data)
  return digest.hexdigest()
 finally:os.close(fd)

def camera481_check(wrapper):
 assert file_sha(wrapper)==CAMERA481
 expected=json.loads(Path(wrapper).read_bytes());assert expected['validated']
 expected=expected['expected'];assert expected['kernel_release']==os.uname().release
 for name,digest in expected['installed_files'].items():assert file_sha(name)==digest,name
 for name,info in expected['modules'].items():
  assert file_sha(info['path'])==info['sha256']
  assert hashlib.sha256(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()).hexdigest()==info['note']
  assert Path('/sys/module',name,'initstate').read_text().strip()=='live'
 assert hashlib.sha256(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id').read_bytes()).hexdigest()==SENSOR468_NOTE
 assert Path('/sys/module/s5k3m5/initstate').read_text().strip()=='live'
 versions={}
 for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
  fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
  if fields.get('P') in expected['packages']:versions[fields['P']]=fields.get('V')
 assert versions==expected['packages']

def eud_off_check():
 # Firmware keeps COM disabled. No MMIO or driver control is part of this gate.
 node=Path('/sys/firmware/devicetree/base/soc@0/serial@88e0000')
 assert (node/'compatible').read_bytes()==b'qcom,sm8150-eud-com\0'
 assert (node/'status').read_bytes()==b'disabled\0'
 assert not Path('/sys/bus/platform/devices/88e0000.serial/driver').exists()
 driver=Path('/sys/bus/platform/drivers/qcom_eud_com')
 assert not list(driver.glob('*.serial'))
 assert not list(Path('/sys/class/tty').glob('ttyEUD*'))
 assert not any('eud' in line.lower() for line in Path('/proc/consoles').read_text().splitlines())
 assert not any(t.startswith(('earlycon=eud','console=eud')) for t in Path('/proc/cmdline').read_text().split())

def validate_activation_guard(guard_path):
 guard_path=secure_file(guard_path);assert guard_path.is_absolute()
 assert guard_path.name=='guard-private.json'
 meta=json.loads(guard_path.read_bytes());assert meta['schema']==EUD_BOOT_SCHEMA
 assert re.fullmatch(r'image501-[a-z0-9-]{8,64}',meta['transaction_id'])
 assert re.fullmatch(r'[0-9a-f]{32,64}',meta['token'])
 assert guard_path.parent==Path('/root/charging-management-20261023')/meta['transaction_id']
 assert meta['old_boot_guard_path']==OLD_BOOT_GUARD
 assert meta['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()==secure_file(OLD_BOOT_GUARD).read_text().strip()
 assert os.uname().machine=='aarch64'
 assert os.uname().release==meta['kernel_release']=='7.3.0-rc6-rmx1931-samurai-k363+'
 assert os.uname().version==meta['kernel_version'] and os.uname().version.startswith('#363 ')
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert file_sha('/etc/samurai-rootfs-release')==meta['rootfs_release_sha256']
 serial=Path('/sys/devices/soc0/serial_number').read_bytes();assert serial.strip()
 compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
 assert b'realme,samurai' in compatible.split(bytes([0]))
 assert hashlib.sha256(serial).hexdigest()==meta['soc_serial_sha256']
 assert hashlib.sha256(compatible).hexdigest()==meta['compatible_sha256']
 assert meta['candidate_boot_sha256']==CANDIDATE_BOOT
 assert meta['rollback_boot_sha256']==ROLLBACK_BOOT and meta['partitions']==['boot','logdump'] and meta['boot_bytes']==100663296
 assert meta['candidate_logdump_sha256']==CANDIDATE_LOGDUMP and meta['rollback_logdump_sha256']==LOGDUMP365 and meta['logdump_bytes']==67108864
 assert meta['image363_sha256']==IMAGE363 and meta['image501_sha256']==IMAGE501
 assert meta['startup500_sha256']==STARTUP500 and meta['startup500_path']=='/usr/local/sbin/samurai-usb' and meta['max_power_ma']==500
 assert file_sha(meta['startup500_path'])==STARTUP500
 eud_off_check()
 assert meta['camera481_expected_sha256']==CAMERA481
 assert meta['charging_manifest_sha256']==R8_MANIFEST
 assert block_sha('/dev/disk/by-partlabel/boot',100663296)==ROLLBACK_BOOT
 # Exact FAT partition identity binds its already-verified ::/Image bytes to
 # Image363 (kernel365/prepare-deployment.py); neither partition is written.
 assert block_sha('/dev/disk/by-partlabel/logdump',67108864)==LOGDUMP365
 manifest_path='/usr/share/samurai-charging/manifest.json';assert file_sha(manifest_path)==R8_MANIFEST
 manifest=json.loads(Path(manifest_path).read_bytes())
 assert manifest['release']==meta['kernel_release'] and manifest['adapter_revision']=='r8'
 for name,digest in manifest['installed_files'].items():assert file_sha(name)==digest,name
 for name,info in manifest['modules'].items():
  assert manifest['installed_files'][info['target']]==info['sha256']
  assert file_sha(info['target'])==info['sha256']
 assert set(manifest['modules'])=={n.replace('_','-') for n in R8_NOTES}
 for name,digest in R8_NOTES.items():
  assert hashlib.sha256(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()).hexdigest()==digest
  assert Path('/sys/module',name,'initstate').read_text().strip()=='live'
 assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'
 assert not Path('/sys/module/samurai_usbin_init').exists()
 assert Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower').read_text().strip()=='500'
 camera481_check(guard_path.parent/'camera481-expected-private.json')
 sample={k:int(v) for k,v in (part.split('=') for part in Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())}
 assert sample['valid']==sample['online']==sample['protection_ok']==1 and 0<=sample['age_ms']<=3000
 assert all(sample[k]==0 for k in ['shadow','error','stop_error','latched','fault','source_inhibit','thermal_inhibit','cycle_timeout','gauge_charge_stop'])
 assert not sample['flags']&0xc000 and sample['session_seconds']<36000
 phase=Path('/run')/(meta['transaction_id']+'-reboot-phase-private.json');assert not phase.exists()
 return meta,Path('/var/lib/samurai')/meta['transaction_id'],phase

assert len(sys.argv)==4 and sys.argv[1]=='--guard'
meta,o,phase=validate_activation_guard(Path(sys.argv[2]))
r=Path('/var/lib/samurai')
