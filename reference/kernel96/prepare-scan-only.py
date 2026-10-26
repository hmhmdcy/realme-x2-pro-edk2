from pathlib import Path
import subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel96');out=Path('/mnt/e/edk2-samurai-out/kernel96')
p=ref/'bt-mgmt-probe.c';source=p.read_text()
backup=out/'bt-mgmt-probe-before-scan-policy.c';assert not backup.exists();backup.write_text(source)
for op in (9,7):
    old=f'if(!rc)rc=command({op},0,&on,1);';new=f'if(!rc)rc=command({op},0,&off,1);'
    assert source.count(old)==1;source=source.replace(old,new)
anchor='    else if(!strcmp(argv[1],"scan")) {\n'
addition='''    else if(!strcmp(argv[1],"scan-policy")) {
        /* Inquiry/LE discovery needs neither incoming connections nor bonding. */
        unsigned char off=0;
        rc=command(9,0,&off,1);
        if(!rc)rc=command(7,0,&off,1);
    }
'''
assert source.count(anchor)==1;source=source.replace(anchor,addition+anchor)
source=source.replace('configure, scan, or','configure, scan-policy, scan, or')
p.write_text(source)
target=out/'bt-mgmt-probe-scan-only';assert not target.exists()
subprocess.run(['aarch64-linux-gnu-gcc','-O2','-Wall','-Wextra','-Wno-misleading-indentation','-static',str(p),'-o',str(target)],check=True)
# Make the initial build generator produce the same stricter helper in a fresh stage.
p=ref/'build-address-tools.py';s=p.read_text()
anchor="(ref/'bt-mgmt-probe.c').write_text(source)\n"
addition="""for op in (9,7):
    source=source.replace(f'if(!rc)rc=command({op},0,&on,1);',f'if(!rc)rc=command({op},0,&off,1);')
source=source.replace('    else if(!strcmp(argv[1],"scan")) {\\n', '''    else if(!strcmp(argv[1],"scan-policy")) {
        unsigned char off=0;
        rc=command(9,0,&off,1);
        if(!rc)rc=command(7,0,&off,1);
    }
    else if(!strcmp(argv[1],"scan")) {
''')
"""
assert s.count(anchor)==1;p.write_text(s.replace(anchor,addition+anchor))
print('Incoming-connectable and bondable disabled in scan configuration')
