"""Read-only identity/physical/environment primitives; no I2C or control writes."""
from pathlib import Path
import hashlib
import json
import os
import re
import time

MANIFEST='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
NOTES={'samurai-usb-input':'f0edb792d30ee1168ee1793e89707aa48b2085c845acde8f472f2c13a03804b0',
 'samurai-gauge-protection':'930e0e1f34e89e4e06a7632ca14a26181975f9f35e55a51209af71480b56fe76',
 'samurai-mp2650':'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'}
REGS=(0x1307,0x1308,0x1310,0x1506,0x1509,0x150b,0x150d,0x1358)
CAMERA=('ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
boot_ms=lambda:int(time.clock_gettime(time.CLOCK_BOOTTIME)*1000)

def read(path,numeric=False):
    try:
        value=Path(path).read_text().strip();return int(value) if numeric else value
    except (OSError,ValueError) as e:return {'error':type(e).__name__,'errno':getattr(e,'errno',None)}

def identity(c):
    boot=read('/proc/sys/kernel/random/boot_id')
    if boot!=c['expected_boot'] or read(c['guard'])!=boot:raise ValueError('R7 boot/guard differs')
    if os.uname().release!='7.3.0-rc6-rmx1931-samurai-k363+' or read('/proc/sys/kernel/tainted')!='0':raise ValueError('release/taint differs')
    if sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())!=MANIFEST:raise ValueError('R8 manifest differs')
    meta=json.loads(Path('/usr/share/samurai-charging/manifest.json').read_bytes())
    for name,digest in meta['installed_files'].items():
        if sha(Path(name).read_bytes())!=digest:raise ValueError('installed package differs: '+name)
    notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in NOTES}
    if notes!=NOTES or any(read('/sys/module/'+n.replace('-','_')+'/initstate')!='live' for n in NOTES):raise ValueError('three live R8 notes differ')
    compat=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
    serial=Path('/sys/devices/soc0/serial_number').read_bytes()
    if b'realme,samurai' not in compat.split(bytes([0])) or not serial.strip():raise ValueError('board identity differs')
    board={'serial_sha256':sha(serial),'compatible_sha256':sha(compat)}
    if c.get('board') is not None and c['board']!=board:raise ValueError('SoC identity changed')
    if not Path('/run/openrc/started/samurai-charging').exists():raise ValueError('charging service marker missing')
    return {'boot':boot,'manifest':MANIFEST,'notes':notes,'board':board}

def environment():
    services=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        comm=read(p/'comm')
        if comm not in ('phoc','phosh','pipewire','wireplumber'):continue
        try:uid=int(re.search(r'^Uid:\s+(\d+)',(p/'status').read_text(),re.M)[1])
        except (OSError,TypeError):continue
        if uid==10000:services.append({'pid':int(p.name),'comm':comm,'uid':uid})
    pm={n:read(Path('/sys/bus/platform/devices')/n/'power/runtime_status') for n in CAMERA}
    m2m=json.loads(Path('/sys/bus/platform/devices/ac10000.icp/m2m_status').read_text())
    if len(services)!=4 or {s['comm'] for s in services}!={'phoc','phosh','pipewire','wireplumber'}:raise ValueError('fresh session services ambiguous')
    if any(v!='suspended' for v in pm.values()) or any(m2m.get(k)!=0 for k in ['users','orphans','jobs','first_error']) or any(m2m.get(k) is not False for k in ['running','fatal','pinned']):raise ValueError('camera not idle')
    return {'services':sorted(services,key=lambda s:s['comm']),'camera_pm':pm,
            'm2m':{k:m2m[k] for k in ['users','orphans','jobs','first_error','running','fatal','pinned']}}

def open_pmic():
    p=Path('/sys/kernel/debug/regmap/0-02')
    if (p/'name').read_text().strip()!='pmic-spmi' or (p/'range').read_text()!='0-ffff\n':raise ValueError('known PMIC debug boundary differs')
    return os.open(p/'registers',os.O_RDONLY|os.O_CLOEXEC)

def pmic(fd):
    result=[]
    for reg in REGS:
        match=re.fullmatch(rb'([0-9a-f]{4}): ([0-9a-f]{2})\n',os.pread(fd,9,reg*9))
        if not match or int(match[1],16)!=reg:raise ValueError('PMIC fixed read failed')
        result.append(int(match[2],16))
    return result

def source():
    base=Path('/sys/class/power_supply')
    return {'usb':{k:read(base/'samurai-usb-input'/k,k!='usb_type') for k in ['online','usb_type','current_max','input_current_limit']},
        'charger':{k:read(base/'mp2650-input'/k,k in ['input_current_limit','constant_charge_current','constant_charge_voltage']) for k in ['input_current_limit','constant_charge_current','constant_charge_voltage','charge_behaviour','health','status']}}

def healthy(row):
    s=row.get('telemetry',{});src=row.get('source',{});usb=src.get('usb',{});chg=src.get('charger',{})
    try:
        safe=(s.get('valid')==s.get('online')==s.get('protection_ok')==1 and s.get('shadow')==0 and 0<=s.get('age_ms',-1)<=3000
            and all(s.get(k,-1)==0 for k in ['error','stop_error','latched','fault','source_inhibit','cycle_timeout','thermal_inhibit','gauge_charge_stop'])
            and type(s.get('flags')) is int and not s['flags']&0xc000)
        full=(s.get('logical_full')==s.get('hold_requested')==s.get('full_holding')==1 and s.get('full_cause') in (1,2,3) and s.get('desired_enable')==0 and s.get('session_seconds')==0)
        mode=full if any(s.get(k,0) for k in ['logical_full','hold_requested','full_holding','full_cause']) else s.get('desired_enable')==1
        return bool(safe and mode and row.get('source_online')==row.get('acok_online')==usb.get('online')==1
            and 50000<=usb['current_max']<=2000000 and 50000<=usb['input_current_limit']
            and 50000<=chg['input_current_limit']<=min(900000,usb['current_max'])
            and 200000<=chg['constant_charge_current']<=250000 and s['budget_ua']==usb['current_max']
            and 2*3712500<=chg['constant_charge_voltage']<=2*4362500 and chg['constant_charge_voltage']%25000==0
            and 160<=s.get('temp_decic',-999)<440 and s.get('thermal_band')==4
            and '[auto]' in chg['charge_behaviour'])
    except (KeyError,TypeError):return False

def current_sample():
    text=Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text()
    telemetry={k:int(v) for k,v in (field.split('=') for field in text.split())}
    return {'telemetry':telemetry,'source':source(),
        'source_online':read('/sys/class/power_supply/samurai-usb-input/online',True),
        'acok_online':read('/sys/class/power_supply/mp2650-input/online',True)}

def save(path,data):
    p=Path(path);temporary=p.with_name(p.name+'.next')
    with temporary.open('w') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
    temporary.replace(p)

def process(receipt):
    p=Path('/proc',str(receipt['pid']))
    try:
        stat=(p/'stat').read_text();parts=stat[stat.rindex(')')+2:].split();ticks=int(parts[19])
        argv=[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]
    except FileNotFoundError:return {'state':'absent'}
    except (OSError,ValueError,IndexError,UnicodeError):return {'state':'unknown'}
    return {'state':'pid_reused' if ticks!=receipt['start_ticks'] else 'zombie' if parts[0]=='Z' else 'alive' if argv==receipt['argv'] else 'unknown',
            'pid':receipt['pid'],'start_ticks':ticks,'argv':argv}
