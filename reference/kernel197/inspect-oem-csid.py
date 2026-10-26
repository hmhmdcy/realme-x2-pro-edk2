from pathlib import Path
root=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source');base=root/'arch/arm64/boot/dts'
hits=0
for p in base.rglob('*.dtsi'):
 if 'sm8150' not in p.name and 'camera' not in p.name:continue
 rows=p.read_text(errors='replace').splitlines()
 for i,l in enumerate(rows):
  if any(x in l.lower() for x in ['acb3000','acb0000','acba000','acb7000']):print(p.relative_to(root),i+1,'\n'.join(rows[max(0,i-6):i+14]));hits+=1
print('matching_nodes',hits)
