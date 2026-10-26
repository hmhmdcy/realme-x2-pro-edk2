from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2'); ref=root/'reference/kernel103'
out=Path('/mnt/e/edk2-samurai-out/kernel103');previous=out.parent/'kernel102'
import json
old_audit=json.loads((previous/'candidate-validation.json').read_text())
source=(root/'reference/kernel102/prepare-package.py').read_text()
source=source.replace('kernel102','kernel103').replace('k102','k103')
source=source.replace("assert sha(out/'boot-partition-before.img')=='b71044d4cee6190e433878af8bc6be12e8179adcf1219981faeb4309c4406543'", "assert sha(out/'boot-partition-before.img')=='4b3e76ae4c1ea5da894f219c20e5ca680785afd880dc2dd9fce09a3f914566ea'")
source=source.replace('2545f18650669910b1923d99dffbd802bc426438327619890150d98832f3d8fe',old_audit['logdump_sha256'])
source=source.replace("(out/'runtime-boot-id-private.txt').read_text().strip()", "(out/'baseline-boot-private.txt').read_text(encoding='utf-8-sig').splitlines()[0]")
source=source.replace('kernel_build=101,logical_stage=102','kernel_build=102,logical_stage=103')
source=source.replace("out.parent/'kernel95/wpa-test-private.conf'", "out.parent/'kernel102/wpa-5g-private.conf'")
(ref/'package-audit-generated.py').write_text(source)
exec(compile(source,str(ref/'package-audit-generated.py'),'exec'))
