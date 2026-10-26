"""Read-only inventory. No service starts, controller power or discovery."""
from pathlib import Path
import argparse
import hashlib
import json
from host import PRIVATE, ssh

SOURCE = r'''
from pathlib import Path
import ctypes,hashlib,json,os,pwd,socket,struct,subprocess,time

deadline=time.monotonic()+55
def remaining(maximum=8):
    return max(0, min(maximum,deadline-time.monotonic()))

def read(path):
    try:return Path(path).read_text().strip()
    except OSError:return None
def run(args, user=False):
    env=os.environ.copy();kw={}
    if remaining()<0.1:return dict(error='read-only inventory deadline exhausted')
    if user:
        account=pwd.getpwuid(10000)
        env.update(HOME=account.pw_dir,USER=account.pw_name,LOGNAME=account.pw_name,
                   XDG_RUNTIME_DIR='/run/user/10000',PULSE_SERVER='unix:/run/user/10000/pulse/native')
        def demote():
            os.setgroups([]);os.setgid(account.pw_gid);os.setuid(account.pw_uid)
        kw['preexec_fn']=demote
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=remaining(),env=env,**kw)
        return dict(rc=p.returncode,out=p.stdout,err=p.stderr)
    except (OSError,subprocess.TimeoutExpired) as e:return dict(error=str(e))
def file(path):
    p=Path(path)
    if not p.is_file():return None
    b=p.read_bytes()
    return dict(sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def elf_note(path):
    data=Path(path).read_bytes()
    if data[:6]!=b'\x7fELF\x02\x01':raise ValueError('Expected ELF64 little endian')
    offset=struct.unpack_from('<Q',data,40)[0]
    size,count,index=struct.unpack_from('<HHH',data,58)
    if size!=64 or not count or index>=count or offset+size*count>len(data):raise ValueError('Invalid ELF section table')
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)]
    strings=sections[index]
    names=data[strings[4]:strings[4]+strings[5]]
    notes=[data[s[4]:s[4]+s[5]] for s in sections if names[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id']
    if len(notes)!=1 or not notes[0]:raise ValueError('Missing unique ELF build ID note')
    return notes[0]

def native_management_info():
    # Reuse kernel130/bt_mgmt.py's proven HCI CONTROL bind and READ-only framing.
    # No power, discovery, pairing, address or other state-changing opcode.
    if remaining(5)<=.1:return dict(error='Inventory deadline exhausted before MGMT query')
    end=time.monotonic()+remaining(5)
    class HCIAddress(ctypes.Structure):
        _fields_=[('family',ctypes.c_ushort),('index',ctypes.c_ushort),('channel',ctypes.c_ushort)]
    s=None
    try:
        s=socket.socket(31,socket.SOCK_RAW|socket.SOCK_CLOEXEC,1)
        s.settimeout(max(.001,end-time.monotonic()))
        address=HCIAddress(31,0xffff,3)
        libc=ctypes.CDLL(None,use_errno=True)
        if libc.bind(s.fileno(),ctypes.byref(address),ctypes.sizeof(address)):
            error=ctypes.get_errno();raise OSError(error,os.strerror(error))
        def request(op,index=0xffff):
            if op not in (3,4,0x36):raise ValueError('Non-observation MGMT opcode refused')
            if time.monotonic()>=end:raise TimeoutError('MGMT observation deadline expired')
            s.settimeout(max(.001,end-time.monotonic()))
            sent=s.send(struct.pack('<HHH',op,index,0))
            if sent not in (0,6):raise ValueError('Short MGMT observation send')
            while time.monotonic()<end:
                s.settimeout(max(.001,end-time.monotonic()))
                raw=s.recv(65535)
                if len(raw)<6:raise ValueError('Short MGMT event')
                event,controller,length=struct.unpack_from('<HHH',raw)
                if len(raw)!=length+6:raise ValueError('MGMT event length mismatch')
                if controller!=index:continue
                data=raw[6:]
                if event==1 and len(data)>=3 and struct.unpack_from('<H',data)[0]==op:
                    status,payload=data[2],data[3:]
                elif event==2 and len(data)==3 and struct.unpack_from('<H',data,1)[0]==op:
                    status,payload=data[0],b''
                else:continue
                if status:raise RuntimeError('MGMT read opcode %04x status %02x'%(op,status))
                return payload
            raise TimeoutError('MGMT observation deadline expired')
        def indexes(op):
            raw=request(op)
            if len(raw)<2:raise ValueError('Short MGMT index count')
            count=struct.unpack_from('<H',raw)[0]
            if len(raw)!=2+2*count:raise ValueError('MGMT index count mismatch')
            return list(struct.unpack_from('<'+'H'*count,raw,2))
        configured=indexes(3);unconfigured=indexes(0x36)
        result=dict(configured=configured,unconfigured=unconfigured,read_only=True)
        if configured==[0] and not unconfigured:
            raw=request(4,0)
            if len(raw)!=280:raise ValueError('Unexpected MGMT READ_INFO length')
            supported,current=struct.unpack_from('<II',raw,9)
            result['info']=dict(address_le_private=raw[:6].hex(),version=raw[6],
                manufacturer=struct.unpack_from('<H',raw,7)[0],supported=supported,current=current,
                le_supported=bool(supported&(1<<9)),le_enabled=bool(current&(1<<9)))
        return result
    except Exception as error:return dict(error=repr(error),read_only=True)
    finally:
        if s is not None:s.close()

r=dict(release=os.uname().release,boot_id=read('/proc/sys/kernel/random/boot_id'),
       taint=read('/proc/sys/kernel/tainted'),uptime=read('/proc/uptime'))
r['gatt_test_dependencies']=run(['python3','-c',
    "import dbus,gi,json,shutil;from gi.repository import GLib,GLibUnix;"
    "print(json.dumps(dict(dbus_version=str(dbus.__version__),gi_version=str(gi.__version__),"
    "glib_unix_signal_add=hasattr(GLibUnix,'signal_add'),btmon=shutil.which('btmon'))))"])
r['native_management_info']=native_management_info()
root='/usr/lib/modules/'+r['release']+'/kernel/drivers/bluetooth/'
module_base='/usr/lib/modules/'+r['release']+'/kernel/'
host_module_paths={'bnep':module_base+'net/bluetooth/bnep/bnep.ko',
                   'uhid':module_base+'drivers/hid/uhid.ko',
                   'hidp':module_base+'net/bluetooth/hidp/hidp.ko'}
paths=[root+'hci_uart.ko',root+'btqca.ko',root+'btbcm.ko',
       '/etc/init.d/bluetooth','/etc/bluetooth/main.conf','/etc/bluetooth/samurai.conf',
       '/usr/sbin/samurai-bluetooth','/usr/sbin/samurai-radio-address',
       '/usr/share/samurai-charging/manifest.json','/etc/pulse/default.pa',
       '/etc/pulse/daemon.conf.d/90-samurai.conf','/usr/sbin/samurai-tqftpserv',*host_module_paths.values()]
r['canonical_paths']={p:str(Path(p).resolve()) for p in paths if Path(p).exists()}
r['files']={p:file(p) for p in paths}
r['owners']={p:run(['apk','info','-W',p]) for p in paths if r['files'][p]}
r['canonical_owners']={p:run(['apk','info','-W',real]) for p,real in r['canonical_paths'].items() if real!=p}
for name in ['bluetooth','hci_uart','btqca','btbcm','bnep','uhid','hidp']:
    r.setdefault('module_notes',{})[name]=file('/sys/module/'+name+'/notes/.note.gnu.build-id')
r['host_protocol_modules']={name:dict(loaded=Path('/sys/module/'+name).is_dir(),
    disk_file=r['files'][path],loaded_note=r['module_notes'][name]) for name,path in host_module_paths.items()}
r['module_provenance']={}
for expected in EXPECTED_MODULES:
    name=expected['name'];path=root+name+'.ko'
    try:
        note=elf_note(path);module=Path('/sys/module/'+name);loaded=module/'notes/.note.gnu.build-id'
        r['module_provenance'][name]=dict(disk_is_expected_r0=r['files'][path]['sha256']==expected['sha256'],
            disk_note_sha256=hashlib.sha256(note).hexdigest(),loaded=module.is_dir(),
            initstate=read(module/'initstate'),loaded_note_available=loaded.is_file(),
            loaded_note_matches_disk=loaded.read_bytes()==note if loaded.is_file() else None)
    except (OSError,ValueError,KeyError,TypeError,struct.error,IndexError) as e:r['module_provenance'][name]=dict(error=str(e))
r['packages']=run(['apk','info','-v'])
r['apk_version']=run(['apk','--version'])
module_tree=Path('/usr/lib/modules')/r['release']
index_paths=[p for p in module_tree.glob('modules.*') if p.is_file()]
r['module_installation_inventory']=dict(
    lib_modules_canonical=str((Path('/lib/modules')/r['release']).resolve()),
    usr_modules_canonical=str(module_tree.resolve()),
    lib_symlink_target=os.readlink('/lib') if Path('/lib').is_symlink() else None,
    indexes={p.name:dict(file=file(p),canonical=str(p.resolve()),
        owner=run(['apk','info','-W',str(p)])) for p in index_paths},
    modules_order_present=(module_tree/'modules.order').is_file())
r['apk_transaction_context']=dict(
    installed_database=file('/lib/apk/db/installed'),world=file('/etc/apk/world'),
    lock_path_exists=Path('/lib/apk/db/lock').exists(),
    commit_hooks={str(p):dict(file=file(p),symlink=p.is_symlink(),
        text=read(p) if not p.is_symlink() and p.is_file() and p.stat().st_size<=65536 else None)
        for p in Path('/etc/apk/commit_hooks.d').glob('*') if p.is_file()})
r['bluez_config']=read('/etc/bluetooth/main.conf')
r['bluez_service']=read('/etc/init.d/bluetooth')
r['bluez_status']=run(['rc-service','bluetooth','status'])
r['management_info']=run(['btmgmt','info'])
r['management_commands']=run(['btmgmt','commands'])
r['module_info']=run(['modinfo',root+'hci_uart.ko'])
r['pulse_info']=run(['pactl','info'],True)
r['pulse_modules']=run(['pactl','-f','json','list','modules'],True)
r['pulse_cards']=run(['pactl','-f','json','list','cards'],True)
r['pulse_sinks']=run(['pactl','-f','json','list','sinks'],True)
r['pulse_sources']=run(['pactl','-f','json','list','sources'],True)
r['pulse_bluez_files']=[str(p) for pattern in ('pulse-*/modules/*blue*','pulseaudio/modules/*blue*') for p in Path('/usr/lib').glob(pattern)]
r['pw_bluez_files']=[str(p) for p in Path('/usr/lib/spa-0.2/bluez5').glob('*')]
r['wireplumber_audio_policy']={str(p):read(p) for base in ['/usr/share/wireplumber/wireplumber.conf.d','/etc/wireplumber/wireplumber.conf.d']
                               for p in Path(base).glob('*pulseaudio*')}
r['audio_processes']=run(['pgrep','-af','pulseaudio|pipewire|wireplumber|callaudiod'])
r['dbus']={}
try:
    if remaining(5)<=.1:raise RuntimeError('Read-only inventory deadline exhausted before D-Bus query')
    import dbus
    bus=dbus.SystemBus(private=True)
    try:
        owner=str(bus.call_blocking('org.freedesktop.DBus','/org/freedesktop/DBus',
            'org.freedesktop.DBus','GetNameOwner','s',('org.bluez',),timeout=max(.001,remaining(5))))
        if remaining(5)<=.1:raise RuntimeError('Read-only inventory deadline exhausted before BlueZ query')
        obj=dbus.Interface(bus.get_object(owner,'/',introspect=False),'org.freedesktop.DBus.ObjectManager').GetManagedObjects(timeout=remaining(5))
        r['dbus']['owner_unique_name']=str(owner)
        # Keep all identities in private evidence; public summary uses counts only.
        r['dbus']['objects']=json.loads(json.dumps(obj,default=str))
    finally:bus.close()
except Exception as e:r['dbus']['error']=repr(e)
r['keys']={str(p):file(p) for p in Path('/var/lib/bluetooth').glob('**/info')}
r['charging']={}
r['charging_inhibit_context']=dict(
    telemetry=read('/sys/bus/i2c/devices/0-005c/telemetry'),
    independent_protection_state=read('/sys/bus/platform/devices/samurai-gauge-protection/protection_state'),
    standard_gauges={p.name:{n:read(p/n) for n in ['status','health','capacity','voltage_now','current_now','temp']}
        for p in Path('/sys/class/power_supply').glob('bq*')},
    raw_i2c_or_read_clear_fault_accessed=False)
for base,names in [('mp2650-input',['status','health','input_current_limit','constant_charge_current','constant_charge_voltage']),
                   ('samurai-usb-input',['online','current_max','input_current_limit','usb_type'])]:
    r['charging'][base]={n:read('/sys/class/power_supply/'+base+'/'+n) for n in names}
r['remoteproc']={p.name:read(p/'state') for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
r['camera_processes']=run(['pgrep','-af','camss|libcamera|ipa_proxy|snapshot'])
r['dmesg']=run(['dmesg'])
r['elapsed_within_budget']=time.monotonic()<=deadline
print(json.dumps(r,sort_keys=True))
'''

def pulse_summary(report):
    query = report.get('pulse_modules', {})
    try:
        if query.get('rc') != 0:
            return None
        rows = json.loads(query['out'])
        if not isinstance(rows, list):
            return None
        return [row['name'] for row in rows if 'bluetooth' in row.get('name', '') or 'bluez' in row.get('name', '')]
    except (ValueError, KeyError, TypeError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-private', type=Path, default=PRIVATE / 'runtime-baseline-private.json')
    parser.add_argument('--summary', type=Path, default=Path(__file__).with_name('runtime-baseline.json'))
    args = parser.parse_args()
    output = args.output_private
    if any(p.exists() or p.is_symlink() or not p.parent.is_dir() for p in [output,args.summary]):
        raise SystemExit('Use new baseline and summary paths with existing parents; do not overwrite/replay')
    lock=json.loads(Path(__file__).resolve().parents[1].joinpath('package-hardening-20261023/source-lock.json').read_text())
    source=SOURCE.replace('EXPECTED_MODULES',repr(lock['modules']))
    # GNU timeout owns the remote process group, including a stalled child query.
    result = ssh('timeout -s TERM -k 3 65 python3 -', input=source.encode(), timeout=80)
    result.check_returncode()
    report = json.loads(result.stdout)
    output.write_bytes(result.stdout)
    packages = report['packages'].get('out', '').splitlines()
    objects = report['dbus'].get('objects', {})
    bluez_known = 'objects' in report['dbus'] and 'error' not in report['dbus']
    adapters = [v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
    devices = [v['org.bluez.Device1'] for v in objects.values() if 'org.bluez.Device1' in v]
    loaded_pulse_bluez = pulse_summary(report)
    summary = dict(read_only=True, release=report['release'], taint=report['taint'],
        bluetooth_module=report['files'][f"/usr/lib/modules/{report['release']}/kernel/drivers/bluetooth/hci_uart.ko"],
        module_provenance=report['module_provenance'],
        host_protocol_modules=report['host_protocol_modules'],
        gatt_test_dependency_query_rc=report['gatt_test_dependencies'].get('rc'),
        native_management_indexes_valid='error' not in report['native_management_info'],
        native_management_query_valid='info' in report['native_management_info'] and 'error' not in report['native_management_info'],
        mgmt_le_supported=report['native_management_info'].get('info',{}).get('le_supported'),
        mgmt_le_enabled=report['native_management_info'].get('info',{}).get('le_enabled'),
        elapsed_within_budget=report['elapsed_within_budget'],
        charging_manifest=report['files']['/usr/share/samurai-charging/manifest.json'],
        packages=[p for p in packages if any(t in p for t in ('bluez','pulse','pipewire','wireplumber','samurai-platform','linux-samurai'))],
        bluez_state_known=bluez_known,
        adapter_count=len(adapters) if bluez_known else None,
        paired_device_count=sum(bool(d.get('Paired')) for d in devices) if bluez_known else None,
        connected_device_count=sum(bool(d.get('Connected')) for d in devices) if bluez_known else None,
        adapter_state=[dict({k: a.get(k) for k in ('Powered','Discovering','Pairable','Discoverable')},
                            service_uuid_count=len(a.get('UUIDs',[]))) for a in adapters] if bluez_known else None,
        pulse_loaded_bluez_modules=loaded_pulse_bluez,
        pulse_loaded_bluez_module_count=len(loaded_pulse_bluez) if loaded_pulse_bluez is not None else None,
        pulse_bluez_file_glob_count=len(report['pulse_bluez_files']),
        pulse_query_rc=report['pulse_info'].get('rc'),
        no_device_changes=True, private_evidence=str(output))
    args.summary.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__ == '__main__':main()
