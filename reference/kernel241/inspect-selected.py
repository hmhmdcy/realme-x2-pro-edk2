from pathlib import Path
import json,re,subprocess,sys
from elfview import Elf

P = Path('/mnt/e/edk2-samurai-out/kernel241')
V = Path('/mnt/e/edk2-samurai-out/kernel238/vendor-source-private/payload/lib64')
mode = sys.argv[1]
if mode == 'calls':
    for lib in ('libgnss.so', 'libloc_api_v02.so'):
        for item in json.loads((P/(lib+'.selected-private.json')).read_text()):
            print('\n'+lib+' '+item['name'])
            lines = item['disassembly'].splitlines()
            for i,line in enumerate(lines):
                if re.search(r'\b(bl|blr|br)\b',line) and not re.search(
                        r'log_|android_log|get_timestamp|memset|syscall|getpid|stack_chk|cfi_|abort|convertQmiSecondary|operator new|operator delete|basic_string|vector|memcpy',line):
                    print(line)
elif mode == 'vtables':
    for lib, addresses in [('libgnss.so',[0x57b10,0x57b90,0x569a0]),('libloc_api_v02.so',[])]:
        e = Elf(V/lib)
        print(lib, 'symbols',len(e.syms),'APS2 relocations',e.packed_count)
        addresses.extend(s['value'] for s in e.syms if s['demangled']=='vtable for LocApiV02')
        for base in addresses:
            print('VTABLE',hex(base),e.describe(base))
            for offset in range(0, 640 if lib=='libloc_api_v02.so' else 64,8):
                item=e.pointer(base+offset)
                print(hex(offset),hex(item['value']),item['name'] or e.describe(item['value']))
elif mode == 'range':
    lib,lo,hi=sys.argv[2:]
    text=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','-C','--start-address='+lo,'--stop-address='+hi,str(V/lib)],text=True)
    print(text)
