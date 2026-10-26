"""Adapt the coherent release build, preserving all completed kernel290 artifacts."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel290/build-boot-kernel.py').read_text()
s=s.replace('15c8639d8badf5d4146bfd1b2c2fcb2460a137e5','8a16fbe17010c1eede868f8b8eb7d1dbd77c81ad')
s=s.replace('34204656424a03b7904c6d079aa0b112dafcec220b2a27b23c7b9afaa4eca8b2','9c1b4f24d42519af211b81fc015c948239ea6cfc1550d197469b07c779053581')
s=s.replace("ROOT.parent/'kernel289/fixes-full-build-validation.json'","ROOT.parent/'kernel290/boot-candidate-build-validation.json'")
s=s.replace("'completed-boot289'","'completed-boot290'")
s=s.replace('input-initramfs290','input-initramfs292').replace('input-initramfs288','input-initramfs290')
s=s.replace('old_initramfs288_preserved','old_initramfs290_preserved')
s=s.replace('stage=290','stage=292').replace("KBUILD_BUILD_VERSION='290'","KBUILD_BUILD_VERSION='292'")
s=s.replace('samurai-k290','samurai-k292').replace("'modules290'","'modules292'").replace('modules-k290','modules-k292')
s=s.replace('verified three ISP fixes','VFE175 standard parameter queue and capability guards')
p=ROOT/'build-boot-kernel.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared coherent kernel292 build; kernel290 retained.')
