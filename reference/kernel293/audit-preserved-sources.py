"""Compare the non-camera audio/display sources with their deployed Image183 receipts."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
audio=json.loads((ROOT.parent/'kernel183/source-validation.json').read_text())['source_sha256']
prior=json.loads((ROOT.parent/'kernel163/build-package-validation.json').read_text())
expected={k:v for k,v in audio.items() if not k.endswith('.dts')}
expected.update({k:v for k,v in prior['prior_display_source_hashes_verified'].items() if k!='MAINTAINERS'})
expected.update(prior['source_sha256'])
rows={n:dict(expected=h,actual=hashlib.sha256((TREE/n).read_bytes()).hexdigest()) for n,h in expected.items()}
different=[n for n,r in rows.items() if r['actual']!=r['expected']]
report=dict(stage=293,source_receipt='Image183 audio/display',checked_files=len(rows),differences=different,
            source_sha256={n:r['actual'] for n,r in rows.items()},read_only=True)
(ROOT/'preserved-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert not different,different
