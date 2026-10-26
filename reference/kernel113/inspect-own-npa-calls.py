from pathlib import Path
import json,re,struct

out=Path('/mnt/e/edk2-samurai-out/kernel113')
image=(out/'original-slpi-analysis-private.elf').read_bytes()
segments=json.loads((out/'original-slpi-analysis-segments-private.json').read_text())
listing=(out/'original-slpi-disassembly-private.txt').read_text().splitlines()
for name in ['original-slpi-text6-disassembly-private.txt','original-slpi-text7-disassembly-private.txt','original-slpi-npa-disassembly-private.txt']:
    if (out/name).exists(): listing.extend((out/name).read_text().splitlines())
needles=['SPI_QUP_DDR','I2C_QUP_DDR','/icb/arbiter','failed client create (error: %d)',
    'npa_create_sync_client_ex failed','SPI_QUP_CORE','I2C_QUP_CORE']
found=[]
for needle in needles:
    start=0
    while True:
        offset=image.find(needle.encode()+bytes([0]),start)
        if offset<0: break
        start=offset+1
        matching=[s for s in segments if s['fileoff']<=offset<s['fileoff']+s['filesz']]
        assert len(matching)==1
        segment=matching[0];address=segment['va']+offset-segment['fileoff']
        signed=address if address<2**31 else address-2**32
        preceding=image.rfind(bytes([0]),max(segment['fileoff'],offset-160),offset)+1
        full=image[preceding:offset+len(needle)].decode('ascii',errors='replace')
        address-=offset-preceding
        signed=address if address<2**31 else address-2**32
        representations=[hex(address),hex(signed),str(address),str(signed)]
        relative_representations=[hex(address&0xffffff)]
        indices=[i for i,line in enumerate(listing) if any(re.search(re.escape(x)+r'(?![0-9a-fA-F])',line) for x in representations)]
        relative_indices=[i for i,line in enumerate(listing) if any(re.search(re.escape(x)+r'(?![0-9a-fA-F])',line) for x in relative_representations)]
        pointer_sites=[];pstart=0
        while True:
            poffset=image.find(struct.pack('<I',address),pstart)
            if poffset<0: break
            pstart=poffset+1
            matches=[s for s in segments if s['fileoff']<=poffset<s['fileoff']+s['filesz']]
            if len(matches)==1:
                s=matches[0]
                pointer_sites.append(dict(segment=s['index'],relative_offset=poffset-s['fileoff'],
                    address=s['va']+poffset-s['fileoff'],fileoff=poffset,
                    words=list(struct.unpack('<'+'I'*12,image[poffset-16:poffset+32]))))
        found.append(dict(name=needle,address=address,segment=segment['index'],instruction_indices=indices,
            relative_indices=relative_indices,full=full,
            pointer_sites=pointer_sites))
(out/'npa-string-xrefs-private.json').write_text(json.dumps(found,indent=2)+'\n')
context=[]
for item in found:
    context.append('\nSTRING '+item['name']+' xrefs='+str(len(item['instruction_indices'])))
    for index in item['instruction_indices']:
        context.extend(listing[max(0,index-14):index+19])
(out/'npa-call-xrefs-private.txt').write_text('\n'.join(context)+'\n')
# Raw addresses and complete disassembly stay in the private analysis artifacts.
def redact(line):
    line=re.sub(r'^\s*[0-9a-fA-F]+:', 'CODE:',line)
    def immediate(match):
        value=int(match.group(0),0)&0xffffffff
        if value>=0x80000000:
            labels=[x['name'] for x in found if x['address']==value]
            return '<'+(labels[0] if labels else 'firmware-pointer')+'>'
        return match.group(0)
    return re.sub(r'-?0x[0-9a-fA-F]+',immediate,line)
for item in found:
    print(json.dumps(dict(name=item['name'],full=item['full'] if len(item['full'])<130 else 'longer-format',segment=item['segment'],xrefs=len(item['instruction_indices']),relative_matches=len(item['relative_indices']),
        pointer_sites=[dict(segment=p['segment'],relative_offset=p['relative_offset'],
            words=['pointer' if x>=0x80000000 else x for x in p['words']]) for p in item['pointer_sites'][:6]])))
    if item['name'] in ['SPI_QUP_DDR','I2C_QUP_DDR']:
        for index in item['instruction_indices'][:6]:
            print('\n'.join(redact(x) for x in listing[max(0,index-38):index+18]))
            previous='\n'.join(listing[max(0,index-38):index])
            vector_addresses=[int(x,0)&0xffffffff for x in re.findall(r'r4 = ##(-?0x[0-9a-f]+)',previous)]
            for vector_address in vector_addresses:
                matches=[s for s in segments if s['va']<=vector_address<s['va']+s['filesz']]
                if len(matches)!=1: continue
                s=matches[0];foff=s['fileoff']+vector_address-s['va']
                words=list(struct.unpack('<4I',image[foff:foff+16]))
                print('NPA_VECTOR_BYTES '+json.dumps(dict(client=item['name'],segment=s['index'],
                    words=['pointer' if x>=0x80000000 else x for x in words])))
                item['vector_words']=words
                item['vector_address']=vector_address
        for index in item['relative_indices'][:6]:
            print('RELATIVE_MATCH '+str(index))
            print('\n'.join(redact(x) for x in listing[max(0,index-10):index+15]))
patterns=[]
for pattern in patterns:
    indices=[i for i,line in enumerate(listing) if re.search(pattern,line)]
    print('PATTERN '+pattern+' count='+str(len(indices)))
    for index in indices[:8]:
        print('\n'.join(redact(x) for x in listing[max(0,index-12):index+15]))
        with (out/'npa-call-xrefs-private.txt').open('a') as destination:
            destination.write('\nPATTERN '+pattern+'\n'+'\n'.join(listing[max(0,index-50):index+60])+'\n')
for item in found:
    if item['name']=='failed client create (error: %d)' and item['segment']==4:
        for index in item['instruction_indices']:
            print('ROOT_NPA_CALLBACK_ERROR_PATH')
            print('\n'.join(redact(x) for x in listing[max(0,index-35):index+5]))
(out/'npa-string-xrefs-private.json').write_text(json.dumps(found,indent=2)+'\n')
