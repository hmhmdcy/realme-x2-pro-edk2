from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');old=r/'reference/kernel126';ref=r/'reference/kernel128'
for name in ['poll-new-boot.ps1','collect-runtime.sh']:
 s=(old/name).read_text().replace('kernel126','kernel128').replace('k126','k128').replace('KERNEL126','KERNEL128').replace('K126','K128').replace('kernel_build=126','kernel_build=128').replace("'^#126 '","'^#128 '")
 (ref/name).write_text(s)
print('K128_FRESH_NATIVE_RUNTIME_OBSERVATION_AND_CAPTURE_READY',flush=True)
