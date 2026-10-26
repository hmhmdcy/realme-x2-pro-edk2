"""Run the target's curve treatment and attenuation, excluding OEM smoothing."""
from pathlib import Path
import ctypes, importlib.util, struct
from unicorn.arm64_const import *
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('hal380', HERE.parent / 'kernel380/hal-machine.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
libm = ctypes.CDLL('libm.so.6')
libm.powf.argtypes = [ctypes.c_float, ctypes.c_float]
libm.powf.restype = ctypes.c_float

class CurveMachine(h.Machine):
    def step(self, u, pc, size, user):
        if pc == 0x5b1960:
            self.instructions += 1
            self.providers[hex(pc)] = self.providers.get(hex(pc), 0) + 1
            values = [struct.unpack('<f', struct.pack('<I', u.reg_read(r)))[0]
                      for r in [UC_ARM64_REG_S0, UC_ARM64_REG_S1]]
            value = libm.powf(*values)
            u.reg_write(UC_ARM64_REG_S0, struct.unpack('<I', struct.pack('<f', value))[0])
            u.reg_write(UC_ARM64_REG_PC, u.reg_read(UC_ARM64_REG_LR))
            return
        return super().step(u, pc, size, user)

    def curves(self, record):
        assert len(record) == 456
        values = struct.unpack('<113fI', record)
        u = self.u
        region = h.DATA + 0x20000
        obj = h.DATA + 0x30000
        reserve = h.DATA + 0x40000
        sp = h.STACK + 0xe0000
        u.mem_write(sp, bytes(0x4000))
        u.mem_write(region, bytes([0xa7]) * 736)
        u.mem_write(obj, bytes(1024))
        u.mem_write(reserve, bytes(1024))
        u.mem_write(region + 260, record[:396])
        # Actual target region offsets: strength,atten-start/end,dark/bright,
        # LCE strength,p0/p1,then the six automatic controls.
        controls = values[99:113]
        for index, offset in enumerate([660, 680, 664, 668, 672, 676, 692, 696, 700, 704, 708, 712]):
            u.mem_write(region + offset, struct.pack('<f', controls[index]))
        u.mem_write(obj + 140, struct.pack('<2f', *controls[12:14]))
        u.mem_write(sp + 240, struct.pack('<Q', obj))
        u.mem_write(sp + 104, struct.pack('<Q', reserve))
        for r, value in [(UC_ARM64_REG_SP, sp), (UC_ARM64_REG_X23, region),
                         (UC_ARM64_REG_X21, region + 260), (UC_ARM64_REG_W8, values[-1])]:
            u.reg_write(r, value)
        u.emu_start(0x35ec64, 0x360560, timeout=2000000, count=100000)
        assert u.reg_read(UC_ARM64_REG_PC) == 0x360560, hex(u.reg_read(UC_ARM64_REG_PC))
        # Jump over the OEM temporal/adaptive block. This deliberately tests
        # these two primitive operations, not the whole Execute function.
        u.reg_write(UC_ARM64_REG_X28, obj)
        u.reg_write(UC_ARM64_REG_X21, region + 260)
        u.reg_write(UC_ARM64_REG_X23, region)
        u.emu_start(0x360ac8, 0x360c3c, timeout=2000000, count=2000)
        assert u.reg_read(UC_ARM64_REG_PC) == 0x360c3c
        assert bytes(u.mem_read(region, 260)) == bytes([0xa7]) * 260
        assert bytes(u.mem_read(region + 716, 20)) == bytes([0xa7]) * 20
        for index, offset in enumerate([660, 680, 664, 668, 672, 676, 692, 696, 700, 704, 708, 712]):
            assert bytes(u.mem_read(region + offset, 4)) == struct.pack('<f', controls[index])
        return bytes(u.mem_read(region + 260, 396))
