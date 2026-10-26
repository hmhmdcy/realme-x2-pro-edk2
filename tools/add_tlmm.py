import io, os, shutil
# 1) copy factory TLMMDxe into our tree
dst = 'Platform/EFI_Binaries/Drivers/Devices/samurai/TLMMDxe'
os.makedirs(dst, exist_ok=True)
src = '/home/cy122/uefifw/realme-rmx1931/Binaries/QcomPkg/Drivers/TLMMDxe'
for fn in ('TLMMDxe.efi', 'TLMMDxe.depex', 'TLMMDxe.inf'):
    if os.path.exists(os.path.join(src, fn)):
        shutil.copyfile(os.path.join(src, fn), os.path.join(dst, fn))
        print('copied', fn)
    else:
        print('MISSING', fn)

# 2) samurai.fdf.inc: add TLMMDxe + revert ButtonsDxe to factory (realme) version
q = 'Platform/Realme/sm8150/samurai.fdf.inc'
t = io.open(q, encoding='utf-8', errors='replace').read()

# revert ButtonsDxe to the extracted realme version (needs TLMM)
t = t.replace('Platform/EFI_Binaries/Drivers/sm8150/ButtonsDxe/ButtonsDxe.depex',
              'Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe/ButtonsDxe.depex')
t = t.replace('Platform/EFI_Binaries/Drivers/sm8150/ButtonsDxe/ButtonsDxe.efi',
              'Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe/ButtonsDxe.efi')
print('ButtonsDxe -> factory(realme) version')

if 'TLMMDxe' not in t:
    block = '''
// Factory TLMMDxe (provides EFI_QCOM_TLMM_PROTOCOL) - required by the factory ButtonsDxe for VOL-/VOL+ GPIO
FILE DRIVER = 8681CC5A-0DF6-441E-B4B8-E915C538F067 {
    SECTION DXE_DEPEX = Platform/EFI_Binaries/Drivers/Devices/samurai/TLMMDxe/TLMMDxe.depex
    SECTION PE32 = Platform/EFI_Binaries/Drivers/Devices/samurai/TLMMDxe/TLMMDxe.efi
    SECTION UI = "TLMMDxe"
}
'''
    t = t.rstrip() + '\n' + block
    print('TLMMDxe FILE DRIVER added')
io.open(q, 'w', encoding='utf-8', newline='\n').write(t)
