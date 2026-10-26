from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel373'
assert json.loads((HERE/'boot-runtime-validation.json').read_text())['passed']
s=(OLD/'camera-check.py').read_text().replace('k373-camera-check-','k375-camera-check-').replace("'stage':373","'stage':375")
s=s.replace("assert json.loads((HERE/'recovery-cleanup-validation.json').read_text())['new_boot_verified']", "assert json.loads((HERE/'boot-runtime-validation.json').read_text())['passed'] and json.loads((HERE/'boot-runtime-validation.json').read_text())['same_boot']")
(HERE/'camera-check.py').write_text(s)
s=(OLD/'camera-check-body.py').read_text().replace('k373-recovered','k374-recovered').replace('stage=373','stage=375')
(HERE/'camera-check-body.py').write_text(s)
print('Prepared375 post-ICP normal camera verification on unchanged recovered374 boot.')
