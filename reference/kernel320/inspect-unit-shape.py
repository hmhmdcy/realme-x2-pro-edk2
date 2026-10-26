"""Assess the retained candidate layout without changing or applying values."""
from pathlib import Path
import json,math,statistics
ROOT=Path('/mnt/e/edk2-samurai-out');P=ROOT/'kernel320';P.mkdir(mode=0o700,exist_ok=True)
unit=json.loads((ROOT/'kernel304/unit-wb-lsc-private.json').read_text())['lsc'][0]['channels']
factory=json.loads((ROOT/'kernel317/factory-lsc-decoded-private.json').read_text())['factory']
def shape(values,w,h):
 mean=statistics.mean(values);variance=statistics.mean([(v-mean)**2 for v in values])
 pairs=[(values[y*w+x],values[y*w+x+1]) for y in range(h) for x in range(w-1)]
 pairs += [(values[y*w+x],values[(y+1)*w+x]) for y in range(h-1) for x in range(w)]
 roughness=statistics.mean([(a-b)**2 for a,b in pairs])/(2*variance) if variance else 0
 return dict(min=min(values),max=max(values),mean=mean,variance=variance,normalized_neighbor_roughness=roughness)
detail=dict(unit_17x13=[shape(v,17,13) for v in unit],unit_13x17=[shape(v,13,17) for v in unit],golden_17x13=[[shape(root['golden'][0]['gains'][c],17,13) for c in ['r','gr','gb','b']] for root in factory])
(P/'candidate-shape-private.json').write_text(json.dumps(detail,indent=2)+'\n')
print(json.dumps({'unit_17x13_roughness':[r['normalized_neighbor_roughness'] for r in detail['unit_17x13']],
 'unit_13x17_roughness':[r['normalized_neighbor_roughness'] for r in detail['unit_13x17']],
 'golden_17x13_roughness_range':[min(r['normalized_neighbor_roughness'] for root in detail['golden_17x13'] for r in root),max(r['normalized_neighbor_roughness'] for root in detail['golden_17x13'] for r in root)],
 'no_phone_operations':True},indent=2))
