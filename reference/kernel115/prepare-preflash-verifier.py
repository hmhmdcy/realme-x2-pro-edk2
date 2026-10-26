from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference')
t=(root/'kernel113/verify-preflash.py').read_text().replace("kernel113')","kernel115')")
t=t.replace('8105116c7af3157ac41aae48350d2d3e4e33e13305c0248da54338bf509e63af','91dd19fbf82664b0e6dca11331bdb84db48a6d154c1df83cd7c7af67c1ebcad3')
t=t.replace("b'#112 SMP PREEMPT'","b'#113 SMP PREEMPT'").replace("== b'0'","== b'512'")
t=t.replace("kernel111/boot-partition-k111.img","kernel113/boot-partition-k113.img").replace("kernel112/logdump-k112-startup.img","kernel113/logdump-k113-sensor-power.img")
t=t.replace('kernel_build=112','kernel_build=113').replace('taint=0','taint=512').replace('KERNEL113_FRESH_PREFLASH','KERNEL115_FRESH_PREFLASH')
(root/'kernel115/verify-preflash.py').write_text(t)
print('KERNEL115_PREFLASH_VERIFIER_READY_WITH_EXACT_CAPTURE_HASH_AND_CURRENT_BOOT113')
