from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel106')
p=Path('/home/cy122/x2pro-linux/linux/.config')
s=p.read_text();old='CONFIG_BOOT_CONFIG_EMBED_FILE="/mnt/e/RealmeX2Pro edk2/reference/kernel106/bootconfig.txt"'
assert s.count(old)==1 and not (out/'radio-bootconfig.txt').exists()
(out/'radio-bootconfig.txt').write_bytes((root/'reference/kernel106/bootconfig.txt').read_bytes())
p.write_text(s.replace(old,'CONFIG_BOOT_CONFIG_EMBED_FILE="/mnt/e/edk2-samurai-out/kernel106/radio-bootconfig.txt"'))
print('BOOTCONFIG_MAKE_DEPENDENCY_PATH_PREPARED')
