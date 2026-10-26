from pathlib import Path
import json,re,subprocess
from elfview import Elf

P=Path('/mnt/e/edk2-samurai-out/kernel241')
V=Path('/mnt/e/edk2-samurai-out/kernel238/vendor-source-private/payload/lib64')
loc=Elf(V/'libloc_api_v02.so')
vt=next(s['value']+16 for s in loc.syms if s['demangled']=='vtable for LocApiV02')
for lo,hi in [(0x306b8,0x30a30),(0x32c1c,0x332cc),(0x332cc,0x33f48),(0x30a30,0x3128c)]:
    text=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','-C','--start-address='+str(lo),'--stop-address='+str(hi),str(V/'libgnss.so')],text=True)
    (P/('gnss-range-'+hex(lo)+'-private.txt')).write_text(text)
    lines=text.splitlines()
    print('RANGE',hex(lo),hex(hi))
    for i,line in enumerate(lines):
        if re.search(r'\b(bl|blr|br)\b',line) and not re.search(r'log_|android_log|get_timestamp|memset|syscall|getpid|stack_chk|cfi_|abort|@@Base\+|operator |vector|basic_string|memcpy',line):
            print('\n'.join(lines[max(0,i-5):i+1]))
            if re.search(r'\bblr\s+x8',line):
                for previous in reversed(lines[max(0,i-10):i]):
                    m=re.search(r'ldr\s+x8, \[x\d+(?:, #(\d+))?\]',previous)
                    if m:
                        offset=int(m[1] or 0)
                        try:
                            p=loc.pointer(vt+offset)
                            print('candidate LocApi vtable slot',offset,p['name'] or loc.describe(p['value']))
                        except ValueError:
                            pass
                        break
