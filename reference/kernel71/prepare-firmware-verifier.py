from pathlib import Path
r=Path('/mnt/e/edk2-samurai-out/kernel71')
s=Path('/mnt/e/edk2-samurai-out/kernel68/verify-firmware.py').read_text()
start=s.index('before_dt=')
end=s.index('\ndata = {}',start)
s=s[:start]+'''import runpy
runpy.run_path(str(root/'validate-dtb.py'))
dt_audit=json.loads((root/'dtb-validation.json').read_text())
'''+s[end:]
s=s.replace('/kernel68','/kernel71').replace('boot-k68-opp.img','boot-k71-touch.img')
s=s.replace("version_before='2184dc1'","version_before='2d389cf'").replace("version_after='2d389cf'","version_after='0819bd5'")
s=s.replace("'cpu7_opp_dtb'","'native_touch_dtb'").replace('sole_semantic_dtb_change=opp_path','semantic_dtb_changes=dt_audit')
(r/'verify-firmware.py').write_text(s)
