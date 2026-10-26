"""Execute the OEM face-smoothing block and complete curve phase sequence."""
from pathlib import Path
import importlib.util, struct
from unicorn.arm64_const import *
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('curve407', HERE.parent / 'kernel407/curve-model.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
h = old.h
GLOBAL = 0x96aac0
SCALE = 0x96baa0

class TemporalMachine(old.CurveMachine):
    def step(self,u,pc,size,user):
        if pc == getattr(self, 'stop_pc', None):
            u.emu_stop()
            return
        if pc == 0x5b1460:
            raise RuntimeError('Unexpected logging: LR='+hex(u.reg_read(UC_ARM64_REG_LR))+
                ' x20='+hex(u.reg_read(UC_ARM64_REG_X20))+
                ' logging='+bytes(u.mem_read(GLOBAL+584,1)).hex()+
                ' w5='+hex(u.reg_read(UC_ARM64_REG_W5)))
        return super().step(u,pc,size,user)

    def evaluate(self, record):
        assert len(record) == 876
        mode = struct.unpack_from('<I', record)[0]
        data = record[4:460]
        control = record[460:472]
        state = record[472:876]
        signal, bps, bypass = struct.unpack('<fII', control)
        face, remaining = struct.unpack_from('<2I', state)
        u = self.u
        region = h.DATA + 0x20000
        obj = h.DATA + 0x30000
        reserve = h.DATA + 0x40000
        sp = h.STACK + 0xe0000
        u.mem_write(sp, bytes(0x4000))
        u.mem_write(region, bytes([0xa7]) * 736)
        u.mem_write(obj, bytes(1024))
        u.mem_write(reserve, bytes(1024))
        u.mem_write(GLOBAL + 8, bytes([face]))
        u.mem_write(GLOBAL + 220, struct.pack('<I', remaining))
        u.mem_write(GLOBAL + 584, b'\0')
        u.mem_write(SCALE, state[8:268])
        u.mem_write(GLOBAL + 2344, state[268:336])
        u.mem_write(GLOBAL + 2412, state[336:404])
        u.mem_write(obj + 448, control)
        u.mem_write(sp + 240, struct.pack('<Q', obj))
        u.mem_write(sp + 104, struct.pack('<Q', reserve))
        u.mem_write(region + 260, data[:396])
        if mode:
            values = struct.unpack('<113fI', data)
            controls = values[99:113]
            for i, offset in enumerate([660, 680, 664, 668, 672, 676, 692, 696, 700, 704, 708, 712]):
                u.mem_write(region + offset, struct.pack('<f', controls[i]))
            u.mem_write(obj + 140, struct.pack('<2f', *controls[12:14]))
        registers = [(UC_ARM64_REG_SP, sp), (UC_ARM64_REG_X23, region),
                     (UC_ARM64_REG_X21, region + 260), (UC_ARM64_REG_X28, obj),
                     (UC_ARM64_REG_X20, GLOBAL), (UC_ARM64_REG_X8, region + 520)]
        if mode:
            registers.append((UC_ARM64_REG_W8, values[-1]))
        for r, value in registers:
            u.reg_write(r, value)
        start, end = (0x35ec64, 0x360c3c) if mode else (0x360560, 0x360ac8)
        # Different modes reuse translated blocks. An explicit hook stop is
        # required when a cached longer block spans the shorter end address.
        self.stop_pc = end
        before = self.instructions
        u.emu_start(start, end, timeout=2000000, count=100000)
        assert u.reg_read(UC_ARM64_REG_PC) == end, hex(u.reg_read(UC_ARM64_REG_PC))
        out = bytes(u.mem_read(region + 260, 396))
        next_state = struct.pack('<2I', u.mem_read(GLOBAL + 8, 1)[0], self.read32(GLOBAL + 220))
        next_state += bytes(u.mem_read(SCALE, 260))
        next_state += bytes(u.mem_read(GLOBAL + 2344, 68))
        next_state += bytes(u.mem_read(GLOBAL + 2412, 68))
        assert bytes(u.mem_read(region, 260)) == bytes([0xa7]) * 260
        assert bytes(u.mem_read(region + 716, 20)) == bytes([0xa7]) * 20
        assert bytes(u.mem_read(obj + 448, 12)) == control
        return out, next_state, self.instructions - before
