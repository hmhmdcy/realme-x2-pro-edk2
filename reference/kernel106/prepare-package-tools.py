from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel106';old=root/'reference/kernel105'
p=ref/'prepare-package.py';assert not p.exists()
s=(old/'prepare-package.py').read_text().replace('kernel105','kernel106').replace('k105','k106')
s=s.replace("prev=out.parent/'kernel104'","prev=out.parent/'kernel105'")
s=s.replace('kernel_build=104,logical_stage=105','kernel_build=105,logical_stage=106')
p.write_text(s)
print('FRESH_LOGDUMP_ONLY_PACKAGE_TOOL_PREPARED')
