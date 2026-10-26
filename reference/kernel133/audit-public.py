from pathlib import Path
r = Path('/mnt/e/RealmeX2Pro edk2')
source = (r / 'reference/kernel130/audit-public.py').read_text()
source = source.replace('129,130]:', '129,130,131,132,133]:')
source = source.replace('range(109,131)', 'range(109,134)')
source = source.replace("r/'reference/kernel130/public-audit.json'", "r/'reference/kernel133/public-audit.json'")
source = source.replace('current_kernel=129,rootfs_generation=130', 'current_kernel=132,rootfs_generation=132')
exec(compile(source, 'privacy-audit-expanded-to-133', 'exec'))
