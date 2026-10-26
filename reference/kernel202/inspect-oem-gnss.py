from pathlib import Path
import hashlib,json,re

private=Path('/mnt/e/edk2-samurai-out/kernel202')
oem=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/arch/arm64/boot/dts/19781')
hits=[]
for path in sorted(oem.glob('*.dts*')):
    lines=path.read_text(errors='replace').splitlines()
    for index,line in enumerate(lines):
        if re.search(r'\bgnss\b|\bgps\b|\blna\b|gps-|gnss-|lna-',line,re.I):
            hits.append(dict(file=path.name,line=index+1,context='\n'.join(lines[max(0,index-3):index+5]),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(private/'oem19781-gnss-source-hits.json').write_text(json.dumps(hits,indent=2)+'\n')
print(json.dumps(dict(stage=202,own_board_dts_directory='19781',matching_contexts=len(hits),files=sorted({h['file'] for h in hits}))))
for hit in hits[:12]: print(json.dumps(hit))
