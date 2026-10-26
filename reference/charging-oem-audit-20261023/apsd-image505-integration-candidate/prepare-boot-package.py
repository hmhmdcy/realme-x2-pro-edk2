"""Reuse the current IRQ carrier constructor, changing its actual two inputs."""
from pathlib import Path
import ast,hashlib
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
original=REF/'charging-ui-audit-20261023/usb-input-irq-boot-candidate/package-boot.py';source=original.read_text()
def replace(before,after):
 global source
 assert source.count(before)==1,(before[:90],source.count(before));source=source.replace(before,after)
replace('"""Default read-only check; one private native-DTB-FFS substitution, never deploys."""','"""Actual505 BDS/native-DTB two-FFS offline carrier; never deploys."""')
replace("CURRENT = OLD / 'boot-gauge501-private.img'","CURRENT = ROOT / 'usb-input-irq-boot-private-01/boot-usb-input-irq-private.img'")
replace("OUT = ROOT / 'usb-input-irq-boot-private-01'","OUT = ROOT / 'apsd-image505-boot-private-01'")
replace("DTB = ROOT / 'usb-input-irq-board-private-01/samurai-usb-input-irq-native-private.dtb'","DTB = ROOT / 'apsd-image505-dtb-private-02/samurai-apsd505-native-private.dtb'")
replace("EFI = ROOT / 'gauge-image501-bds-private-01/BdsDxe/OUTPUT/BdsDxe.efi'","EFI = Path('/home/cy122/charging-management-20261023/apsd-image505-bds-01/BdsDxe.efi')")
replace("PAIR = REF / 'charging-ui-audit-20261023/usb-input-irq-board-candidate/pair-manifest.json'","PAIR = HERE / 'assembly-inputs.json'")
start=source.index('def check_local():');end=source.index('\ndef equal_tail(',start)
source=source[:start]+'''def check_local():
    assert file_sha(CURRENT)=='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
    pair=json.loads(PAIR.read_bytes())
    assert pair['prepared'] and not pair['installed']
    assert file_sha(EFI)==pair['artifacts']['BDS_EFI']['sha256']=='939345bc6bb9f114e77da614e33e36d5bd4bfc59f8c17d3bc547bf2f35084f0b'
    assert file_sha(DTB)==pair['artifacts']['native_DTB']['sha256']=='d5fa6cabdd231fed8e35b26cb17e8d4c59068705d90285775b7ede48f2e338d3'
    assert pair['actual_cmdline'].encode('utf-16-le') in EFI.read_bytes()
    assert file_sha(OLD/'result.json')=='2d46df7c53dd8378800160d542bb9ded28067039b6403b87d47d625664bb31b8'
    previous=json.loads((OLD/'result.json').read_bytes());assert previous['passed']
    for name in ['FVMAIN.inf','FVMAIN_COMPACT.inf']:assert file_sha(OLD/name)==previous['artifacts'][name]
    for tool in m['tools']:assert file_sha(Path(tool['path']))==tool['sha256']
    old=unpack(CURRENT);mods=fv(old['main']);assert len(mods)==101 and old['used']==LIMIT
    assert sha(mods[BDS]['sections'][1][1])=='071a628bd34c8d4715c0b57b89a219e21c236d2f5f16c8d82bd832de4dcc196b'
    assert sha(mods[DT]['sections'][0][1])=='13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f'
    return old

def verify_main(main,old):
    a,b=raw_files(old['main']),raw_files(main)
    assert list(a)==list(b) and len(b)==101
    changed=[guid for guid in a if a[guid]['full']!=b[guid]['full']];assert set(changed)=={BDS,DT}
    assert all(a[guid]['full']==b[guid]['full'] for guid in a if guid not in {BDS,DT})
    previous,mods=fv(old['main']),fv(main)
    assert all((previous[guid]['type'],previous[guid]['attrs'])==(mods[guid]['type'],mods[guid]['attrs']) for guid in a)
    bs=mods[BDS]['sections'];assert [item[0] for item in bs]==[0x13,0x10,0x15]
    assert bs[0][2]==previous[BDS]['sections'][0][2] and bs[2][2]==previous[BDS]['sections'][2][2]
    assert bs[1][1]==EFI.read_bytes() and mods[DT]['sections'][0][1]==DTB.read_bytes()
    return dict(changed_complete_FFS=changed,other99_complete_FFS_exact=True,BDS_depex_UI_exact=True,BDS_EFI_and_native_DTB_exact=True)

'''+source[end:]
marker="        inputs = extract_current(old['main'], OUT / 'inputs')"
insert='''
        bds=fv(old['main'])[BDS]['sections']
        (OUT/'sections/BDS.dpx').write_bytes(bds[0][2]);(OUT/'sections/BDS.ui').write_bytes(bds[2][2])
        tool('GenSec',['-s','EFI_SECTION_PE32','-o',OUT/'sections/BDS.pe32',EFI],'BDS-PE32')
        tool('GenFfs',['-t','EFI_FV_FILETYPE_DRIVER','-g',BDS,'-o',inputs[BDS],'-oi',OUT/'sections/BDS.dpx','-oi',OUT/'sections/BDS.pe32','-oi',OUT/'sections/BDS.ui'],'BDS-FFS')
'''
replace(marker,marker+insert)
source=source.replace("HERE / 'result.json'","HERE / 'boot-package-result.json'").replace('boot-usb-input-irq-private.img','boot-apsd505-private.img')
# The previous replacement also touched CURRENT; keep its original known name.
source=source.replace("ROOT / 'usb-input-irq-boot-private-01/boot-apsd505-private.img'","ROOT / 'usb-input-irq-boot-private-01/boot-usb-input-irq-private.img'")
source=source.replace('only separately approved --execute-boot','authorized offline --execute-boot; no device access')
ast.parse(source)
target=HERE/'package-boot.py'
with target.open('x') as file:file.write(source)
print(dict(prepared=True,constructor_sha256=hashlib.sha256(source.encode()).hexdigest()))
