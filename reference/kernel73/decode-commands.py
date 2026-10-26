from pathlib import Path
import json
root = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel73')
def commands(data):
    result, off = [], 0
    while off < len(data):
        assert len(data)-off >= 7
        typ,last,vc,ack,delay,hi,lo = data[off:off+7]
        size = hi*256+lo
        assert size and off+7+size <= len(data)
        payload = data[off+7:off+7+size]
        result.append(dict(type=typ,last=last,vc=vc,ack=ack,delay=delay,data=payload.hex(' ')))
        off += 7+size
    return result
for name in ('live60-on', 'live60-off', 'live90-on', 'live90-off'):
    decoded = commands((root/(name+'.bin')).read_bytes())
    (root/(name+'.json')).write_text(json.dumps(decoded,indent=2)+'\n')
    print(name, len(decoded), 'commands')
    if name.startswith('live60'):
        for c in decoded:
            print('%02x delay=%3d %s' % (c['type'], c['delay'], c['data']))
