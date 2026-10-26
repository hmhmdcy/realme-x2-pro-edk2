from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel124'
t=(r/'reference/kernel122/audit-public.py').read_text()
t=t.replace('118,119,120,121,122]:','118,119,120,121,122,123,124]:')
t=t.replace("'sessions/122-complete-k121-rootfs-and-verified-build-cleanup.md']","'sessions/122-complete-k121-rootfs-and-verified-build-cleanup.md','sessions/123-camss-dt-dma-interconnect-and-strict-disabled-validation.md','sessions/124-native-cphy-shared-rail-and-frequency-contract.md']")
t=t.replace('range(109,123)','range(109,125)').replace("'122' in hardware","'124' in hardware").replace('offline_camera_candidate=121','offline_camera_candidate=124').replace('reference/kernel122/public-audit.json','reference/kernel124/public-audit.json');(ref/'audit-public.py').write_text(t)
t=(r/'reference/kernel123/verify-syntax.py').read_text().replace('123','124');(ref/'verify-syntax.py').write_text(t)
t=(r/'reference/kernel123/close-host-volumes.py').read_text().replace('123','124');(ref/'close-host-volumes.py').write_text(t)
print('K124_FINAL_AUDIT_SYNTAX_AND_VOLUME_CLOSURE_PREPARED')
