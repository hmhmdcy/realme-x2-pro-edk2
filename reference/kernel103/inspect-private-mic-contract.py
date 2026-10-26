from pathlib import Path
import io,tarfile,xml.etree.ElementTree as ET
out=Path('/mnt/e/edk2-samurai-out/kernel103');previous=out.parent/'kernel102'
def walk(data):
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        for m in t:
            if not m.isfile():continue
            b=t.extractfile(m).read()
            if m.name.endswith('.tar'):yield from walk(b)
            elif 'mixer_paths' in m.name and m.name.endswith('.xml'):yield m.name,b
derived=[]
for name,b in walk((previous/'stock-audio-contract.tar').read_bytes()):
    tree=ET.fromstring(b)
    print('DMIC defaults',[(x.get('name'),x.get('value')) for x in tree.findall('ctl') if 'DMIC MUX' in x.get('name','')])
    for p in tree.findall('path'):
        if p.get('name') in ('handset-mic','handset-mic-raw','speaker-mic','headset-mic','dmic0','dmic1','dmic2','amic2'):
            controls=[dict(x.attrib) for x in p.findall('ctl')]
            refs=[x.get('name') for x in p.findall('path')]
            derived.append(dict(file=name,path=p.get('name'),controls=controls,references=refs))
(out/'oem-mic-contract-derived-private.json').write_text(__import__('json').dumps(derived,indent=2)+'\n')
for d in derived:
    print(d['file'],d['path'],d['references'])
    print([(c.get('name'),c.get('value')) for c in d['controls'] if any(s in c.get('name','') for s in ('AMIC','DMIC','ADC','DEC','TX','MIC_BIAS','MIC BIAS'))])
print('matching_paths',len(derived))
