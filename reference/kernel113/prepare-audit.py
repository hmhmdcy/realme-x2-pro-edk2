from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference')
text=(ref/'kernel112/audit-public.py').read_text()
text=text.replace('pmos-samurai-kernel112/initramfs','pmos-samurai-kernel113/initramfs')
old="for path in (private / 'kernel112').glob('*.tar'):"
new="for path in [* (private / 'kernel112').glob('*.tar'), * (private / 'kernel113').glob('*.tar')]:"
assert text.count(old)==1; text=text.replace(old,new)
text=text.replace("'sessions/112-startup-sensor-registry-and-reboot.md']]", "'sessions/112-startup-sensor-registry-and-reboot.md', 'sessions/113-sensor-power-and-extended-rpc.md']]")
text=text.replace('当前部署Linux #112','当前部署Linux #113')
text=text.replace('reference/kernel112/public-audit.json','reference/kernel113/public-audit.json')
(ref/'kernel113/audit-public.py').write_text(text)
print('KERNEL113_PUBLIC_IDENTITY_PIN_UUID_AND_15_GROUP_AUDIT_PREPARED')
