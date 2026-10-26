from pathlib import Path
import json,os,shutil
os.umask(0o077);here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213');private.mkdir(mode=0o700)
previous=here.parent/'kernel212'
assert json.loads((previous/'final-health-validation.json').read_text())['taint']==0
shutil.copyfile(private.parent/'kernel212/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
(here/'host.py').write_text((previous/'host.py').read_text().replace("Path('/mnt/e/edk2-samurai-out/kernel212')","Path('/mnt/e/edk2-samurai-out/kernel213')"))
plan=dict(stage=213,previous_turn_classification='progress:212 no-flash warm boot, persisted CPU ISP,6 RGB frames with first black, clean final health and96 native files archived.',state='213 transport prepared, no device or source change yet.',guard='/var/lib/samurai/k212-runtime/boot-id-private.txt',transport='reference/kernel213/host.py',transition_pending=False,next='Fresh runtime and installed libcamera/SDK audit; backport verified IMX471 helper and investigate cached initial ISP params. Build isolated candidate, verify actual first frame and gain before product install. Full five-camera/peripheral goal active.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('213 prepared;212 classified as verified progress. No transition or product mutation.')
