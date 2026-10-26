from pathlib import Path
import subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel96')
out=Path('/mnt/e/edk2-samurai-out/kernel96')
qrtr=out.parent/'kernel88/qrtr'
target=out/'dms-mac-read-verified';assert not target.exists()
subprocess.run(['aarch64-linux-gnu-gcc','-O2','-Wall','-Wextra','-Werror','-static','-I'+str(qrtr/'include'),str(ref/'dms-mac-read.c'),str(qrtr/'lib/qrtr.c'),str(qrtr/'lib/logging.c'),'-o',str(target)],check=True)
source=(ref.parent/'kernel92/bt-mgmt-probe.c').read_text()
old='!(argc==3 && !strcmp(argv[1],"test-address"))'
new='!(argc==3 && (!strcmp(argv[1],"test-address") || !strcmp(argv[1],"dms-address")))'
assert source.count(old)==1;source=source.replace(old,new)
source=source.replace('else if(!strcmp(argv[1],"test-address")) {','else if(!strcmp(argv[1],"test-address") || !strcmp(argv[1],"dms-address")) {')
old='''        /* A temporary locally administered test identity, never a factory address. */
        if(n!=6 || extra!=EOF || (address[5]&3)!=2)return 2;'''
new='''        /* DMS bytes are little-endian on this handset (installed HAL verified).
         * The caller must validate the read-only DMS response's provenance.
         * SET_PUBLIC_ADDRESS changes the controller's runtime identity only. */
        if(n!=6 || extra!=EOF)return 2;
        unsigned zero=0,notff=0;for(unsigned i=0;i<6;i++){zero|=address[i];notff|=address[i]^255;}
        if(!zero || !notff)return 2;
        unsigned flags=!strcmp(argv[1],"dms-address")?0:2;
        if((address[5]&3)!=flags)return 2;'''
assert source.count(old)==1;source=source.replace(old,new)
source=source.replace('or test-address PRIVATE_FILE','or test-address/dms-address PRIVATE_FILE')
for op in (9,7):
    source=source.replace(f'if(!rc)rc=command({op},0,&on,1);',f'if(!rc)rc=command({op},0,&off,1);')
source=source.replace('    else if(!strcmp(argv[1],"scan")) {\n', '''    else if(!strcmp(argv[1],"scan-policy")) {
        unsigned char off=0;
        rc=command(9,0,&off,1);
        if(!rc)rc=command(7,0,&off,1);
    }
    else if(!strcmp(argv[1],"scan")) {
''')
source=source.replace('configure, scan, or','configure, scan-policy, scan, or')
(ref/'bt-mgmt-probe.c').write_text(source)
target=out/'bt-mgmt-probe';assert not target.exists()
subprocess.run(['aarch64-linux-gnu-gcc','-O2','-Wall','-Wextra','-Wno-misleading-indentation','-static',str(ref/'bt-mgmt-probe.c'),'-o',str(target)],check=True)
print('Bounded address tools built; not embedded in initramfs')
