from pathlib import Path
root = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel73')
old = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel71/verify-firmware.py').read_text()
script = old.replace('/kernel71','/kernel73').replace('boot-k71-touch.img','boot-k73-display.img')
script = script.replace("version_before='2d389cf'", "version_before='0819bd5'")
script = script.replace("version_after='0819bd5'", "version_after='bd23aaa'")
script = script.replace("'native_touch_dtb'", "'native_display_dtb'")
script = script.replace("runpy.run_path(str(root/'validate-dtb.py'))", "runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel73/validate-dtb.py')")
(root/'verify-firmware.py').write_text(script)
old_dt = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel71/validate-dtb.py').read_text()
helper = old_dt[old_dt.index('def cells('):old_dt.index('ac,bc=')]
(root/'dtb-canonical.py').write_text('import struct\n'+helper)
