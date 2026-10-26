from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference')
ref=root/'kernel115'
for name in ['enable-eud.ps1','read-early-eud.ps1','collect-runtime.sh']:
    t=(root/'kernel113'/name).read_text().replace('kernel113','kernel115').replace('k113','k115').replace('KERNEL113','KERNEL115').replace("'^#113 '","'^#115 '")
    (ref/name).write_text(t)
print('KERNEL115_BOUNDED_EUD_AND_NATIVE_RUNTIME_CAPTURE_TOOLS_READY')
