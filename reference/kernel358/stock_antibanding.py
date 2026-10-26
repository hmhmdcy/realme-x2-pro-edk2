"""Run the complete retained OEM anti-banding function; only logging is stubbed."""
from pathlib import Path
import struct, sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel329'))
from stock_emulator import StockMath, OBJECT, OUT, LOGGER
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_PC, UC_ARM64_REG_LR

class StockAntibanding(StockMath):
    def __init__(self,path):
        super().__init__(path,0x2a438,0x2a79c)
        self.write(0x5bcb0,'<Q',LOGGER)
        self.visited=set()

    def _step(self,uc,pc,size,user):
        self.visited.add(pc)
        if pc in [0x586f0,LOGGER]:
            self.stub_calls+=1
            uc.reg_write(UC_ARM64_REG_X0,0)
            uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
            return
        super()._step(uc,pc,size,user)

    def adjust(self,config,exposure):
        self.uc.mem_write(OBJECT,bytes(0x6000))
        self.write(OBJECT+8,'<Q',OBJECT+0x4000)
        self.write(OBJECT+0x4000,'<Q',OBJECT+0x5000)
        self.write(OBJECT+0x5000+56,'<Q',config['blanking'])
        self.write(OBJECT+0x5000+128,'<I',config['method'])
        self.write(OBJECT+48,'<f',config['threshold'])
        self.write(OBJECT+1404,'<IQ',config['enabled'],config['period'])
        self.write(OBJECT+1432,'<f',config['min_gain'])
        self.write(OBJECT+1440,'<QQ',config['min_ns'],config['max_ns'])
        before=struct.pack('<f4xQf12x',exposure['gain'],exposure['time'],exposure['index'])
        self.uc.mem_write(OUT,before)
        self.call()
        result=bytes(self.uc.mem_read(OUT,len(before)))
        assert result[4:8]==before[4:8] and result[16:]==before[16:]
        return struct.unpack_from('<f',result)[0],struct.unpack_from('<Q',result,8)[0]
