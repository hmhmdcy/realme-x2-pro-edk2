from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2/reference')
s=(r/'kernel72/flash-logdump.ps1').read_text()
s=s.replace('k72','k73').replace('kernel72','kernel73')
s=s.replace('logdump-k73-ncm-ssh.img','logdump-k73-display-deps.img')
s=s.replace('13a8263dac6c75f909b6fa8dc89520949c7009ddcb9de2b2a5f6125e26d4292b',
            'c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7')
s=s.replace('kernel71\\logdump-k71-touch.img','kernel73\\logdump-k73-display.img')
s=s.replace('f6837573c908eddad7a2d8d0ab494c259ff99a9a5b85878e3b6747d40b2d3fb8',
            'a4435ab347d3e857de88183b6d07969b47306cde1a5370489c95f384935968da')
for name in ('confirm-devices','confirm-product','confirm-size-logdump','flash-logdump','reboot','flash-validation.json'):
    s=s.replace("'"+name+"'", "'deps-"+name+"'").replace('\\'+name,'\\deps-'+name)
s=s.replace("@('-s','62bc28a1','deps-reboot')", "@('-s','62bc28a1','reboot')")
(r/'kernel73/flash-deps.ps1').write_text(s)
cpio=(r/'kernel72/validate-initramfs.py').read_text().replace('/kernel72','/kernel73')
(r/'kernel73/validate-initramfs.py').write_text(cpio)
