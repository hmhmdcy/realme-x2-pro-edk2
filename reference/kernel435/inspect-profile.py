from pathlib import Path
import json
import host,storage
storage.mount.mounted_build();P=host.PRIVATE
roots=json.loads((P.parent/'kernel432/sunny_s5kgw1-gtm-trees-private.json').read_text())
selections=json.loads((P.parent/'kernel431/sunny_s5kgw1-gtm-selections-private.json').read_text())
print(json.dumps(dict(selections=[dict(tag=tag,context=context,uid=r['uid']) for tag,context,r in selections],root_keys=list(roots[0]),reserve_keys=list(roots[0]['reserve']))))
print(json.dumps([dict(uid=r['uid'],enabled=r['enabled'],reserve_flags=r['reserve']) for r in roots if r['uid']==21]))
import yaml
v=yaml.safe_load((P.parent/'kernel431/factory-s5kgw1-private.yaml').read_text())
print(json.dumps(dict(root_keys=list(v),version=v['version'],modes=[dict(match=m.get('match'),tone_keys=list(m.get('ipe_tone',{}))) for m in v.get('modes',[v])]),default=str))
