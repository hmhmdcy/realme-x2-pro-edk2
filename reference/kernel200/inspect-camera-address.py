from pathlib import Path
import json,os

common=Path('/var/lib/samurai/k195-modules/probe-q-reset-address.py').read_text().split('report=dict(',1)[0]
common=common.replace("out=root/'k195-q-reset'","out=root/'k200-camera-address-inspection'").replace('k195-baseline','k200-runtime').replace("read_text().strip()=='512'","read_text().strip()=='0'")
exec(compile(common,'<verified-read-only-camera-prefix>','exec'))
r=dict(stage=200,p_reset=sample(0),q_reset=sample(3),at4=snapshot(4),at8=snapshot(8))
(out/'summary-private.json').write_text(json.dumps(r,indent=2)+'\n')
os.close(gfd);os.close(ifd)
print(json.dumps(dict(stage=200,p_reset=r['p_reset'],q_reset=r['q_reset'],at4_identity=r['at4']['identity'],at8_identity=r['at8']['identity'],at4_outputs_disabled=all(x['enable']['data']==[0] for x in r['at4'].get('ldos',[])),read_only=True)))
