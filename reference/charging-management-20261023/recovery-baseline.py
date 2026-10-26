"""Read current camera baseline before/after a coordinated recovery restart."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import time

def baseline():
    packages = {}
    for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
        fields = dict(l.split(':',1) for l in block.splitlines() if ':' in l)
        if fields.get('P') in EXPECTED['packages']: packages[fields['P']] = fields['V']
    assert packages == EXPECTED['packages']
    modules = {}
    for name, info in EXPECTED['modules'].items():
        p = Path(subprocess.check_output(['modinfo','-n',name], text=True).strip())
        raw = p.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == info['sha256']
        off = struct.unpack_from('<Q',raw,40)[0]
        stride,count,strings = struct.unpack_from('<HHH',raw,58)
        sections = [struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)]
        ns = raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
        note = next(s for s in sections if ns[s[0]:].split(b'\0')[0] == b'.note.gnu.build-id')
        loaded = Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()
        assert loaded == raw[note[4]:note[4]+note[5]]
        modules[name] = {'sha256':info['sha256'], 'loaded_note_matches_disk':True}
    camera = Path('/sys/bus/platform/devices/ac10000.icp')
    m2m = json.loads((camera / 'm2m_status').read_text())
    core = json.loads((camera / 'state').read_text())
    assert not any(m2m[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
    assert m2m['jobs'] == m2m['completed'] == m2m['direct_completed']
    assert not any(core[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held',
        'remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped',
        'imported_buffers','imported_bytes'])
    pm = {n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip()
          for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']}
    assert all(v == 'suspended' for v in pm.values())
    services = {n:[] for n in ['phoc','phosh','pipewire','wireplumber']}
    for p in Path('/proc').glob('[0-9]*'):
        try:
            n=(p/'comm').read_text().strip()
            if n in services and (p/'stat').read_text().rsplit(')',1)[1].split()[0] != 'Z':
                services[n].append({'pid':int(p.name),'uid':p.stat().st_uid})
        except OSError: pass
    assert all(len(v) == 1 and v[0]['uid'] == 10000 for v in services.values())
    assert not any(Path('/sys/module',n).exists() for n in
        ['samurai_mp2650','samurai_gauge_protection','samurai_usb_input'])
    return {'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'release':os.uname().release,'taint':int(Path('/proc/sys/kernel/tainted').read_text()),
        'packages':packages,'modules':modules,'m2m':m2m,'core':core,'pm':pm,'services':services,
        'charger_driver':Path('/sys/bus/i2c/devices/0-005c/driver').resolve().name}

data = baseline()
assert data['release'] == '7.3.0-rc6-rmx1931-samurai-k363+'
assert data['charger_driver'] == 'mp2650'
print(json.dumps(data))
