"""Bounded native Linux Bluetooth management observations. Payloads stay private."""
import ctypes, errno, json, os, select, socket, struct, time
from pathlib import Path

READ_ONLY = {0x0001, 0x0002, 0x0003, 0x0004, 0x0036, 0x0037}
SCAN_OPS = READ_ONLY | {0x0005, 0x0006, 0x0007, 0x0009, 0x0023, 0x0024}

class HCIAddress(ctypes.Structure):
    _fields_ = [('family', ctypes.c_ushort), ('index', ctypes.c_ushort), ('channel', ctypes.c_ushort)]

def open_channel(channel):
    s = socket.socket(31, socket.SOCK_RAW | socket.SOCK_CLOEXEC, 1)
    address = HCIAddress(31, 0xffff, channel)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.bind(s.fileno(), ctypes.byref(address), ctypes.sizeof(address)):
        e = ctypes.get_errno(); s.close(); raise OSError(e, os.strerror(e))
    return s

class Management:
    def __init__(self, path, allow_scan=False):
        self.socket = open_channel(3)
        self.log = Path(path).open('x', encoding='utf-8')
        self.allowed = SCAN_OPS if allow_scan else READ_ONLY

    def record(self, **item):
        self.log.write(json.dumps(dict(monotonic=time.monotonic(), **item))+'\n'); self.log.flush()

    def receive(self, timeout):
        if not select.select([self.socket], [], [], timeout)[0]: return None
        b = self.socket.recv(65535)
        if len(b) < 6: raise ValueError('short management header')
        event, index, length = struct.unpack_from('<HHH', b)
        if len(b) != length+6: raise ValueError('management payload length mismatch')
        self.record(kind='event', event=event, index=index, payload=b[6:].hex())
        return event, index, b[6:]

    def command(self, op, index=0xffff, payload=b'', allow_failure=False):
        if op not in self.allowed: raise ValueError('operation outside observation/scan allowlist')
        b = struct.pack('<HHH', op, index, len(payload))+payload
        n = self.socket.send(b)
        self.record(kind='command', op=op, index=index, payload=payload.hex(), send_result=n)
        if n not in (0, len(b)): raise ValueError('short management send')
        end = time.monotonic()+12
        while time.monotonic() < end:
            event = self.receive(min(0.5, end-time.monotonic()))
            if event is None: continue
            ev, idx, p = event
            if idx != index: continue
            if ev == 1 and len(p) >= 3 and struct.unpack_from('<H', p)[0] == op:
                status, data = p[2], p[3:]
            elif ev == 2 and len(p) == 3 and struct.unpack_from('<H', p, 1)[0] == op:
                status, data = p[0], b''
            else: continue
            self.record(kind='response', op=op, index=index, status=status, payload=data.hex())
            if status and not allow_failure: raise RuntimeError(f'MGMT op={op:#06x} status={status:#04x}')
            return status, data
        raise TimeoutError(f'MGMT op={op:#06x}')

    def indexes(self, op):
        status, p = self.command(op)
        if len(p) < 2: raise ValueError('short index count')
        count = struct.unpack_from('<H', p)[0]
        if len(p) != 2+2*count: raise ValueError('index count/length mismatch')
        return list(struct.unpack_from('<'+'H'*count, p, 2))

    def info(self, index):
        status, p = self.command(4, index)
        if len(p) != 280: raise ValueError(f'READ_INFO unexpected size {len(p)}')
        return dict(index=index, address_le=p[:6].hex(), version=p[6], manufacturer=struct.unpack_from('<H', p, 7)[0],
                    supported=struct.unpack_from('<I', p, 9)[0], settings=struct.unpack_from('<I', p, 13)[0])

    def close(self):
        self.socket.close(); self.log.close()

def snapshot(mgmt):
    configured=mgmt.indexes(3); unconfigured=mgmt.indexes(0x36)
    assert len(configured)+len(unconfigured) == 1, 'require exactly one controller'
    result=dict(configured=configured, unconfigured=unconfigured)
    if configured: result['info']=mgmt.info(configured[0])
    else:
        status,p=mgmt.command(0x37,unconfigured[0]); assert len(p)==10
        manufacturer,supported,missing=struct.unpack('<HII',p)
        result['configuration']=dict(manufacturer=manufacturer,supported=supported,missing=missing)
    return result

if __name__ == '__main__':
    import sys
    dest=Path(sys.argv[1]); dest.mkdir(mode=0o700)
    m=Management(dest/'mgmt-private.jsonl')
    try:
        result=snapshot(m)
        (dest/'state-private.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(configured_count=len(result['configured']),unconfigured_count=len(result['unconfigured']),
                             missing_configuration=result.get('configuration',{}).get('missing'))))
    finally: m.close()
