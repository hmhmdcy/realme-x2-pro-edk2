# Range-reading of regular OZIP follows the framing documented by B. Kerler's
# MIT-licensed oppo_ozip_decrypt (pinned below).  Its program is read, not run.
from pathlib import Path
import ast,hashlib,io,json,re,struct,subprocess,sys,time,urllib.request,zipfile
from threading import Lock
from Crypto.Cipher import AES

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
recipe=out/'ozip-decrypt-reference-private'
revision='eb93b3f3fb7be3564cc546c88699ab4062a04928'
assert subprocess.check_output(['git','-C',str(recipe),'rev-parse','HEAD']).decode().strip()==revision
source=(recipe/'ozipdecrypt.py').read_bytes()
tree=ast.parse(source)
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
keys=ast.literal_eval(next(n.value for n in main.body if isinstance(n,ast.Assign) and
    len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='keys'))
assert all(re.fullmatch('[0-9A-F]{32}',key) for key in keys)
probe=next(p for p in json.loads((ref/'older-realme-package-links.json').read_text())['probes']
    if p['version']=='RMX1931_11.A.11')
assert probe['http_status']==206 and probe['oppo_encryption_magic']
url=probe['url']; total=int(probe['content_range'].split('/')[-1])
head=0x1050; stride=0x4010; chunk=stride*16
cache=out/'a11-range-cache-private'; cache.mkdir(mode=0o700,exist_ok=True)
received=0; used={}; retry_events=[]; accounting=Lock()
bulk=None; bulk_proof=None
if (ref/'a11-bulk-range-validation.json').exists():
    bulk_proof=json.loads((ref/'a11-bulk-range-validation.json').read_text())
    assert bulk_proof['version']==probe['version'] and bulk_proof['source_url']==url
    bulk=(out/'a11-modem-bulk-private.bin').read_bytes()
    assert len(bulk)==bulk_proof['bytes']==bulk_proof['end']-bulk_proof['start']+1
    assert hashlib.sha256(bulk).hexdigest()==bulk_proof['sha256']
def physical(start,end):
    global received
    assert 0<=start<=end<total and end-start+1<=chunk
    path=cache/f'{start:010d}-{end:010d}.bin'
    size=end-start+1
    if bulk is not None and bulk_proof['start']<=start<=end<=bulk_proof['end']:
        payload=bulk[start-bulk_proof['start']:end-bulk_proof['start']+1]
        assert len(payload)==size
    elif path.exists():
        payload=path.read_bytes(); assert len(payload)==size
    else:
        assert received+size<=128*1024*1024
        for attempt in range(1,4):
            try:
                # urllib intermittently yielded zero bytes from this endpoint
                # even with a full length header; curl read the same range.
                # Keep its headers/errors private and still verify every range.
                temporary=path.with_suffix('.curl.tmp')
                headers=path.with_suffix('.curl.headers-private.txt')
                errors=path.with_suffix('.curl.errors-private.txt')
                with errors.open('wb') as error_file:
                    subprocess.run(['curl','--fail','--silent','--show-error','--location',
                        '--connect-timeout','10','--max-time','30','--max-filesize',str(size),
                        '--header','Cache-Control: no-cache','--header','Pragma: no-cache',
                        '--range',f'{start}-{end}','--dump-header',str(headers),
                        '--output',str(temporary),
                        url.replace('/osupdate/R','/osupdate/%52',1)],
                        stdout=subprocess.DEVNULL,stderr=error_file,check=True,timeout=35)
                metadata=headers.read_text(errors='replace')
                statuses=re.findall(r'^HTTP/\S+ (\d+)',metadata,re.M)
                assert statuses and statuses[-1]=='206'
                ranges=re.findall(r'^content-range:\s*(.*?)\r?$',metadata,re.I|re.M)
                assert ranges and ranges[-1].strip()==f'bytes {start}-{end}/{total}'
                assert temporary.stat().st_size==size
                payload=temporary.read_bytes()
                temporary.replace(path)
                break
            except Exception as error:
                event=dict(start=start,end=end,attempt=attempt,error_type=type(error).__name__)
                with accounting:
                    retry_events.append(event)
                    with (cache/'range-retries-private.jsonl').open('a') as file:
                        file.write(json.dumps(event)+'\n')
                if attempt==3: raise
                time.sleep(attempt)
        assert path.is_file() and path.stat().st_size==size
        with accounting: received+=size
    with accounting: used[path.name]=hashlib.sha256(payload).hexdigest()
    return payload

encrypted=physical(head,head+15)
matches=[bytes.fromhex(key) for key in keys if AES.new(bytes.fromhex(key),AES.MODE_ECB).decrypt(encrypted).startswith(b'PK\x03\x04')]
assert len(matches)==1,'no unique key for ZIP signature'
aes=AES.new(matches[0],AES.MODE_ECB)
print('A11_UNIQUE_OZIP_KEY_MATCH_ZIP_HEADER_VERIFIED',flush=True)
def block_end(base):
    end=min(total-1,head+base+chunk-1)
    if bulk is not None and bulk_proof['start']<=head+base<=bulk_proof['end']:
        end=min(end,bulk_proof['end'])
    return end

class RemoteZip(io.RawIOBase):
    def __init__(self): self.pos=0; self.blocks={}; self.size=total-head
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        if self.pos<0: raise ValueError('negative offset')
        return self.pos
    def read(self,size=-1):
        if size<0: size=self.size-self.pos
        size=min(size,self.size-self.pos)
        if size<=0: return b''
        assert size<=96*1024*1024,'unexpectedly large ZIP read'
        pieces=[]; end=self.pos+size
        while self.pos<end:
            base=(self.pos//chunk)*chunk
            if base not in self.blocks:
                raw=bytearray(physical(head+base,block_end(base)))
                for offset in range(0,len(raw),stride):
                    if len(raw)-offset>=16:
                        raw[offset:offset+16]=aes.decrypt(raw[offset:offset+16])
                self.blocks[base]=bytes(raw)
            raw=self.blocks[base]; offset=self.pos-base
            count=min(end-self.pos,len(raw)-offset); assert count>0
            pieces.append(raw[offset:offset+count]); self.pos+=count
        return b''.join(pieces)

with zipfile.ZipFile(RemoteZip()) as archive:
    entries=[dict(name=x.filename,compressed_bytes=x.compress_size,bytes=x.file_size,
        compression=x.compress_type,crc32=f'{x.CRC:08x}') for x in archive.infolist()]
    candidates=[x for x in archive.infolist() if x.filename in
        ('NON-HLOS.bin','firmware-update/NON-HLOS.bin','modem.img','firmware-update/modem.img')]
    assert len(candidates)==1,[(x.filename,x.compress_size) for x in archive.infolist() if 'modem' in x.filename.lower() or 'non-hlos' in x.filename.lower()]
    item=candidates[0]
    assert item.compress_size<96*1024*1024 and item.file_size<256*1024*1024
    print(json.dumps(dict(selected_entry=item.filename,compressed_bytes=item.compress_size,
        uncompressed_bytes=item.file_size,zip_directory_entries=len(entries))),flush=True)
    if '--directory-only' in sys.argv:
        bulk_start=head+(item.header_offset//chunk)*chunk
        bulk_end=min(total-1,head+item.header_offset+item.compress_size+65536)
        directory=dict(version=probe['version'],url=url,package_bytes=total,
            selected_entry=item.filename,compressed_bytes=item.compress_size,
            uncompressed_bytes=item.file_size,zip_crc32=f'{item.CRC:08x}',
            physical_bulk_start=bulk_start,physical_bulk_end=bulk_end,
            bytes_to_read=bulk_end-bulk_start+1,firmware_not_yet_extracted=True)
        (ref/'a11-directory-validation.json').write_text(json.dumps(directory,indent=2)+'\n')
        print(json.dumps(directory),flush=True)
        sys.exit(0)
    # Independent byte ranges can be fetched together, then still decoded and
    # checked by zipfile. No candidate survives without the entry CRC passing.
    begin=(item.header_offset//chunk)*chunk
    end=min(total-head-1,item.header_offset+item.compress_size+65536)
    bases=list(range(begin,(end//chunk+1)*chunk,chunk))
    assert len(bases)*chunk<=96*1024*1024
    def prefetch(base):
        physical(head+base,block_end(base))
    # Main-thread subprocess probes succeeded on intervals the threaded reader
    # could not finish. Fetch one range at a time, matching those probes.
    for index,base in enumerate(bases,1):
        prefetch(base)
        if index%32==0: print(f'A11_MODEM_RANGES_VERIFIED {index}/{len(bases)}',flush=True)
    target=out/'a11-reference-private';target.mkdir(mode=0o700,exist_ok=True)
    modem=archive.read(item)  # ZIP CRC is verified by the standard library.
    (target/'modem.img').write_bytes(modem)
    (target/'zip-directory-private.json').write_text(json.dumps(entries,indent=2)+'\n')

report=dict(version=probe['version'],url=url,package_bytes=total,
    recipe_source='https://github.com/bkerler/oppo_ozip_decrypt',recipe_revision=revision,
    recipe_sha256=hashlib.sha256(source).hexdigest(),external_program_executed=False,
    partial_range_download=True,full_package_downloaded=False,
    read_ranges_verified=len(used),range_bytes_used=sum(int(n.split('-')[1].split('.')[0])-int(n.split('-')[0])+1 for n in used),
    fresh_bytes_received=received,range_retry_events=retry_events,network_transport='curl',
    cache_control_no_cache=True,equivalent_percent_encoded_filename_used=True,
    range_requests_serialized=True,zip_directory_entries=len(entries),
    bulk_range_used=bulk is not None,bulk_range_sha256=bulk_proof['sha256'] if bulk is not None else None,
    selected_entry=item.filename,modem_bytes=len(modem),
    modem_sha256=hashlib.sha256(modem).hexdigest(),selected_entry_zip_crc_verified=True,
    slpi_version_not_yet_verified=True,phone_changed=False)
(cache/'ranges-private.json').write_text(json.dumps(used,indent=2)+'\n')
(ref/'a11-package-range-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
