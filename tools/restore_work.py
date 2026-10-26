import io, os, shutil
q = 'Platform/Realme/sm8150/samurai.fdf.inc'
t = io.open(q, encoding='utf-8', errors='replace').read()
# 1) ButtonsDxe back to the WORKING shared sm8150 version
t = t.replace('Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe/ButtonsDxe.depex',
              'Platform/EFI_Binaries/Drivers/sm8150/ButtonsDxe/ButtonsDxe.depex')
t = t.replace('Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe/ButtonsDxe.efi',
              'Platform/EFI_Binaries/Drivers/sm8150/ButtonsDxe/ButtonsDxe.efi')
# 2) drop the experimental TLMMDxe block
import re
t2 = re.sub(r'\n// Factory TLMMDxe.*?\n\}\n', '\n', t, flags=re.S)
if t2 != t:
    print('TLMMDxe block removed')
t = t2
io.open(q, 'w', encoding='utf-8', newline='\n').write(t)
# 3) remove the copied TLMMDxe files
d = 'Platform/EFI_Binaries/Drivers/Devices/samurai/TLMMDxe'
if os.path.isdir(d):
    shutil.rmtree(d)
    print('removed', d)
