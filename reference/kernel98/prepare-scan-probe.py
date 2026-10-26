from pathlib import Path
import hashlib, subprocess

ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel98')
out = Path('/mnt/e/edk2-samurai-out/kernel98')
source = (ref.parent/'kernel96/bt-mgmt-probe.c').read_text()
source = source.replace('#include <time.h>', '#include <time.h>\n#include <errno.h>')
old = '(!strcmp(argv[1],"test-address") || !strcmp(argv[1],"dms-address"))'
assert source.count(old)==2
source=source.replace(old, '(!strcmp(argv[1],"test-address") || !strcmp(argv[1],"dms-address") || !strcmp(argv[1],"scan"))', 1)
old='    fd=socket(31,SOCK_RAW|SOCK_CLOEXEC,1);'
assert source.count(old)==1
source=source.replace(old, '''    long scan_seconds=30;
    if(argc==3 && !strcmp(argv[1],"scan")) {
        char *end;errno=0;scan_seconds=strtol(argv[2],&end,10);
        if(errno || !*argv[2] || *end || scan_seconds<1 || scan_seconds>120)return 2;
    }
    fd=socket(31,SOCK_RAW|SOCK_CLOEXEC,1);''')
old='''        if((u16(b)==1 || u16(b)==2) && n>=9 && u16(b+6)==op && u16(b+2)==idx) {
            printf("command=0x%04x status=0x%02x payload=",op,b[8]);
            for(int i=9;i<n;i++) printf("%02x",b[i]); puts("");
            return b[8]?1:0;
        }'''
assert source.count(old)==1
source=source.replace(old, '''        if(u16(b+2)==idx && ((u16(b)==1 && n>=9 && u16(b+6)==op) ||
           (u16(b)==2 && n==9 && u16(b+7)==op))) {
            unsigned status=u16(b)==1?b[8]:b[6];
            printf("command=0x%04x status=0x%02x payload=",op,status);
            for(int i=9;i<n;i++) printf("%02x",b[i]); puts("");
            return status?1:0;
        }''')
old='''        unsigned char type=7; rc=command(0x23,0,&type,1);
        if(!rc) {unsigned char b[4096];time_t end=time(NULL)+30;int ended=0;
            while(time(NULL)<end) {int n=receive(b,1000);if(n){event(b,n);if(u16(b)==0x13 && n==8 && !b[7]){ended=1;break;}}}
            if(!ended) rc=command(0x24,0,&type,1);
        }'''
assert source.count(old)==1
source=source.replace(old, '''        unsigned char type=7;time_t end=time(NULL)+scan_seconds;
        unsigned restarts=0;rc=command(0x23,0,&type,1);
        if(!rc) {unsigned char b[4096];int active=1;
            while(time(NULL)<end && !rc) {
                int n=receive(b,1000);if(!n)continue;event(b,n);
                if(u16(b)==0x13 && n==8 && u16(b+2)==0 && !b[7]) {
                    active=0;
                    if(time(NULL)<end) {
                        if(++restarts>12){rc=1;break;}
                        rc=command(0x23,0,&type,1);active=!rc;
                    }
                }
            }
            if(active){int stopped=command(0x24,0,&type,1);if(!rc)rc=stopped;}
        }''')
assert not (ref/'bt-mgmt-probe.c').exists() and not (out/'bt-mgmt-probe-scan-window').exists()
(ref/'bt-mgmt-probe.c').write_text(source)
subprocess.run(['aarch64-linux-gnu-gcc','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static',str(ref/'bt-mgmt-probe.c'),'-o',str(out/'bt-mgmt-probe-scan-window')],check=True)
print('Bounded scan-window probe SHA256='+hashlib.sha256((out/'bt-mgmt-probe-scan-window').read_bytes()).hexdigest())
