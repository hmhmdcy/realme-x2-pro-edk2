from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel321/collect-packages.py').read_text().replace('import host','import host,storage')
for a,b in [('packages321-r26','packages342-r27'),('packages-config321-r26','packages-config342-r27'),('candidate321-r26','candidate342-r27'),('libcamera321-lsc-built','libcamera342-r27-built'),('stage=321','stage=342'),('CAMSS321','CAMSS342'),('99990.7.2-r26','99990.7.2-r27'),('0.1.0-r21','0.1.0-r22')]:s=s.replace(a,b)
s=s.replace("(SDK/'packages342-r27')","(storage.candidate().parent/'packages342-r27')").replace("(SDK/'packages-config342-r27')","(storage.candidate().parent/'packages-config342-r27')")
s=s.replace("host.PRIVATE.parent/'kernel316/runtime-repository/forward'","host.PRIVATE.parent/'kernel321/runtime-repository/forward'")
s=s.replace("build=SDK/'work/libcamera342-r27-built/src/libcamera-v0.7.2/output'","build=storage.candidate()/'src/libcamera-v0.7.2/output'")
start=s.index("candidate=SDK/'candidate342-r27'");end=s.index("(host.PRIVATE/'new-ipa-signature.log')",start)
s=s[:start]+'''candidate=SDK/'candidate342-r27';candidate.mkdir(exist_ok=True);assert not any(candidate.iterdir())
subprocess.run(['mount','--bind',str(prefix),str(candidate)],check=True,capture_output=True)
try:
 with storage.sdk_candidate():
  verify='/work/libcamera/src/libcamera-v0.7.2/output/src/apps/ipa-verify/ipa_verify'
  q=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH=/candidate342-r27/usr/lib',verify,
   '/candidate342-r27/usr/lib/libcamera/ipa/ipa_camss_vfe.so'],capture_output=True,timeout=30)
finally:subprocess.run(['umount',str(candidate)],check=True,capture_output=True)
'''+s[end:]
(HERE/'collect-packages.py').write_text(s)
