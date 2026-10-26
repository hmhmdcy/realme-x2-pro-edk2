from pathlib import Path
import re,subprocess
from elfview import Elf
P=Path('/mnt/e/edk2-samurai-out/kernel241')
V=Path('/mnt/e/edk2-samurai-out/kernel238/vendor-source-private/payload/lib64')
targets={'libloc_core.so':['LocContext::injectFeatureConfig','ContextBase::readConfig'],
         'libgnss.so':['GnssAdapter::GnssAdapter()'],'libloc_api_v02.so':['setGnssBiases','locClientRegisterEventMask']}
for lib,patterns in targets.items():
 e=Elf(V/lib)
 frames=subprocess.check_output(['readelf','--debug-dump=frames',str(V/lib)],text=True)
 ranges=[(int(a,16),int(b,16)) for a,b in re.findall(r'pc=([0-9a-f]+)\.\.([0-9a-f]+)',frames)]
 for pattern in patterns:
  sym=next(s for s in e.syms if s['shndx'] and pattern in s['demangled'])
  start,end=sym['value'],sym['value']+sym['size']
  if sym['size']==4:
   import capstone
   cs=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_LITTLE_ENDIAN)
   ins=next(cs.disasm(e.read(start,4),start));assert ins.mnemonic=='b'
   start=int(ins.op_str.lstrip('#'),0)
   end=next(b for a,b in ranges if a==start)
  asm=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','-C','--start-address='+str(start),'--stop-address='+str(end),str(V/lib)],text=True)
  (P/(lib+'-body-'+hex(start)+'-private.txt')).write_text(asm)
  print(lib,sym['demangled'],hex(sym['value']),'real body',hex(start),hex(end))
  lines=asm.splitlines()
  for i,line in enumerate(lines):
   if (pattern=='GnssAdapter::GnssAdapter()' and '#1848' in line) or (pattern!='GnssAdapter::GnssAdapter()' and re.search(r'\b(bl|blr|br)\b',line) and not re.search(r'log_|android_log|get_timestamp|memset|syscall|getpid|stack_chk|cfi_|abort',line)):
    print('\n'.join(lines[max(0,i-4):i+1]))
