from pathlib import Path
import hashlib,importlib.util,json
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
source=(HERE.parent/'kernel306/decode-tele-bls.py').read_text()
inputs=[('sunny_imx319',298,'sunny-imx319-tuning-private.bin','9c8609ec7d2d0e70bbbc3809209fb446af26105892aa56a97a242f1b40775196'),
 ('qtech_s5k3m5sx',306,'qtech-s5k3m5sx-tuning-private.bin','a9059286f6acf1c5d76a1f943e9f62bf3358c019f1e0b419c24b073fec56da1b'),
 ('sunny_imx471',324,'sunny_imx471-tuning-private.bin','f07e6e6ce99ce2fdff54703f87c8f00be18b719d992b37591cec91d090e1928e')]
rows=[]
for variant,stage,name,digest in inputs:
 text=source.replace("raw=(P/'qtech-s5k3m5sx-tuning-private.bin').read_bytes()",f"raw=(P.parent/'kernel{stage}'/'{name}').read_bytes()")
 text=text.replace('a9059286f6acf1c5d76a1f943e9f62bf3358c019f1e0b419c24b073fec56da1b',digest).replace('tele-',variant+'-').replace('stage=306','stage=438')
 scope=dict(__file__=str(HERE/(variant+'-bls-generated.py')));exec(compile(text,scope['__file__'],'exec'),scope)
 ife=[r for r in scope['roots'] if r['name']=='bls12_ife']
 selected_values=sorted({tuple(leaf['values']) for root in ife for leaf in root['leaves']})
 rows.append(dict(variant=variant,source_sha256=digest,ife_roots=len(ife),ife_regions=sum(len(r['leaves']) for r in ife),root_enable_values=sorted({r['enabled'] for r in ife}),all_ife_regions_same=len(selected_values)==1,offset_thresholds=selected_values))
(P/'ife-bls-candidates-private.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
