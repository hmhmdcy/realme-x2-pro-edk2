import io, re
# 1) remove DIAGKEY block -> restore normal boot flow (safety)
p = 'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c'
s = io.open(p, encoding='utf-8', errors='replace').read()
if 'DIAGKEY' in s:
    s = re.sub(r'\n  /\* DIAGKEY-BEGIN.*?/\* DIAGKEY-END \*/\n', '\n', s, flags=re.S)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
    print('DIAGKEY removed ->', 'DIAGKEY' not in s)
else:
    print('DIAGKEY not present')

# 2) samurai.fdf.inc: use the shared (cepheus-proven) ButtonsDxe
q = 'Platform/Realme/sm8150/samurai.fdf.inc'
t = io.open(q, encoding='utf-8', errors='replace').read()
old_e = 'Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe/ButtonsDxe.efi'
old_d = 'Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe/ButtonsDxe.depex'
if 'Drivers/sm8150/ButtonsDxe' in t:
    print('ButtonsDxe already shared')
elif old_e in t:
    t = t.replace(old_d, 'Platform/EFI_Binaries/Drivers/sm8150/ButtonsDxe/ButtonsDxe.depex')
    t = t.replace(old_e, 'Platform/EFI_Binaries/Drivers/sm8150/ButtonsDxe/ButtonsDxe.efi')
    io.open(q, 'w', encoding='utf-8', newline='\n').write(t)
    print('ButtonsDxe -> shared sm8150 version')
else:
    print('ButtonsDxe anchor NOT found')
