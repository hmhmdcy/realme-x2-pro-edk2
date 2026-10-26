from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2')
code=(r/'reference/kernel124/audit-public.py').read_text()
code=code.replace('[114,115,117,118,119,120,121,122,123,124]','[114,115,117,118,119,120,121,122,123,124,125]')
code=code.replace("'sessions/124-native-cphy-shared-rail-and-frequency-contract.md']","'sessions/124-native-cphy-shared-rail-and-frequency-contract.md','sessions/125-native-cpas-qos-full-iova-window-and-mount-serialization.md']")
code=code.replace('range(109,125)','range(109,126)').replace("'124' in hardware","'125' in hardware").replace('offline_camera_candidate=124','offline_camera_candidate=125').replace('reference/kernel124/public-audit.json','reference/kernel125/public-audit.json')
exec(compile(code,'public-audit125','exec'),{})
