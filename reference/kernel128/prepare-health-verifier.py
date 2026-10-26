from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128'
s=(r/'reference/kernel126/verify-final-health-and-bundle.py').read_text()
s=s[:s.index("runpy.run_path(str(ref/'ensure-build-volume.py'))")]
s=s.replace('kernel126','kernel128').replace('current_kernel=126','current_kernel=128').replace('firmware-deployment-package-validation.json','boot-package-validation.json')
s=s.replace("log=after.decode();report=dict(","assert data['wifi-profile-owner.txt']==b'0:0:600\\n'\nfreq=float(re.search(r'freq: ([\\d.]+)',data['wlan-link-private.txt'].decode())[1]);assert freq==5180\nlog=after.decode();report=dict(wlan_frequency_mhz=freq,initial_console_warning_count=log.count('unable to open an initial console'),")
(ref/'verify-final-health.py').write_text(s)
print('K128_FINAL_HEALTH_VERIFIER_BOUND_TO_CURRENT_BOOT_AND_5GHZ',flush=True)
