"""Read-only local source search for the current HAL's AF configuration.

OEM binaries, listings and values remain under the private output directory.
No phone, network, SDK, build, deployment or existing candidate modification.
"""
from pathlib import Path
import ast
import ctypes as C
import ctypes.util
import hashlib
import importlib.util
import io
import json
import os
import re
import struct
import subprocess
import sys
import tarfile
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out')
spec = importlib.util.spec_from_file_location('af_config_storage449', HERE.parent/'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
BUILD = storage.mount.mounted_build()
PRIVATE = P/'kernel453/af-config-source'
PRIVATE.mkdir(exist_ok=True)
TARGET_SHA = 'e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
STABLE = ['AF-PROFILE-NEXT.md', 'inspect-af-profile.py', 'af-profile-validation.json',
          'AF-INDIVIDUAL-NEXT.md', 'inspect-af-individual.py', 'af-individual-validation.json']

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(1024*1024):
            h.update(chunk)
    return h.hexdigest()

def write(name, value):
    (PRIVATE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

class LocalOzip(io.RawIOBase):
    """Local-only framing from retained bkerler eb93b3f3 reference."""
    def __init__(self, path):
        self.file = path.open('rb')
        assert self.file.read(12) == b'OPPOENCRYPT!'
        recipe = P/'kernel113/ozip-decrypt-reference-private'
        revision = subprocess.check_output(['git','-C',str(recipe),'rev-parse','HEAD']).decode().strip()
        assert revision == 'eb93b3f3fb7be3564cc546c88699ab4062a04928'
        source = (recipe/'ozipdecrypt.py').read_bytes()
        main = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        keys = ast.literal_eval(next(n.value for n in main.body if isinstance(n, ast.Assign) and
                               len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='keys'))
        self.head, self.stride, self.chunk = 0x1050, 0x4010, 0x4010*64
        self.file.seek(self.head)
        first = self.file.read(16)
        matches = [bytes.fromhex(k) for k in keys if NativeAES(bytes.fromhex(k)).decrypt(first).startswith(b'PK\x03\x04')]
        assert len(matches) == 1, 'No unique local OZIP key'
        self.aes = NativeAES(matches[0])
        self.pos, self.size, self.cached_base, self.cached = 0, path.stat().st_size-self.head, -1, b''
        self.recipe_sha = hashlib.sha256(source).hexdigest()

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        assert self.pos >= 0
        return self.pos
    def read(self, size=-1):
        size = min(self.size-self.pos, size if size>=0 else self.size-self.pos)
        pieces, end = [], self.pos+size
        while self.pos < end:
            base = (self.pos//self.chunk)*self.chunk
            if self.cached_base != base:
                self.file.seek(self.head+base)
                raw = bytearray(self.file.read(min(self.chunk,self.size-base)))
                for offset in range(0,len(raw),self.stride):
                    if len(raw)-offset >= 16:
                        raw[offset:offset+16] = self.aes.decrypt(raw[offset:offset+16])
                self.cached_base, self.cached = base, bytes(raw)
            offset = self.pos-base
            count = min(end-self.pos,len(self.cached)-offset)
            assert count > 0
            pieces.append(self.cached[offset:offset+count])
            self.pos += count
        return b''.join(pieces)

class NativeAES:
    """Use the host's existing OpenSSL AES implementation; no new dependency."""
    def __init__(self, key):
        self.lib=C.CDLL(ctypes.util.find_library('crypto'))
        self.schedule=C.create_string_buffer(256)
        self.lib.AES_set_decrypt_key.argtypes=[C.c_void_p,C.c_int,C.c_void_p]
        self.lib.AES_set_decrypt_key.restype=C.c_int
        self.lib.AES_decrypt.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p]
        self.lib.AES_decrypt.restype=None
        assert len(key)==16 and self.lib.AES_set_decrypt_key(key,128,self.schedule)==0
    def decrypt(self, raw):
        assert len(raw)==16
        output=C.create_string_buffer(16)
        self.lib.AES_decrypt(bytes(raw),output,self.schedule)
        return output.raw

class NativeBrotli:
    """Streaming calls to the already installed libbrotlidec ABI."""
    def __init__(self):
        self.lib=C.CDLL(ctypes.util.find_library('brotlidec'))
        self.lib.BrotliDecoderCreateInstance.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p]
        self.lib.BrotliDecoderCreateInstance.restype=C.c_void_p
        self.lib.BrotliDecoderDecompressStream.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.POINTER(C.c_void_p),C.POINTER(C.c_size_t),C.POINTER(C.c_void_p),C.POINTER(C.c_size_t)]
        self.lib.BrotliDecoderDecompressStream.restype=C.c_int
        self.lib.BrotliDecoderDestroyInstance.argtypes=[C.c_void_p]
        self.state=self.lib.BrotliDecoderCreateInstance(None,None,None)
        assert self.state
        self.done=False
    def process(self, raw):
        assert not self.done
        source=C.create_string_buffer(raw)
        available=C.c_size_t(len(raw))
        pointer=C.c_void_p(C.addressof(source))
        pieces=[]
        while True:
            target=C.create_string_buffer(1024*1024)
            room=C.c_size_t(len(target))
            output=C.c_void_p(C.addressof(target))
            result=self.lib.BrotliDecoderDecompressStream(self.state,C.byref(available),C.byref(pointer),C.byref(room),C.byref(output),None)
            assert result in (1,2,3), 'Brotli stream rejected'
            pieces.append(target.raw[:len(target)-room.value])
            if result==1:
                assert available.value==0
                self.done=True
                break
            if result==2:
                assert available.value==0
                break
        return b''.join(pieces)
    def is_finished(self): return self.done
    def __del__(self):
        if getattr(self,'state',None): self.lib.BrotliDecoderDestroyInstance(self.state)

def packages():
    facts = []
    for tag, path in [('1330',Path('/mnt/e/系统rom/RMX1931_11_OTA_1330_all_19781_downgrade.ozip')),
                      ('1340',Path('/mnt/e/RMX1931_11_OTA_1340_all_2QCxQYdkxpql.ozip'))]:
        with path.open('rb') as f:
            encrypted = f.read(12) == b'OPPOENCRYPT!'
        reader = LocalOzip(path) if encrypted else path
        with zipfile.ZipFile(reader) as z:
            fact = dict(tag=tag,path=str(path), bytes=path.stat().st_size, framed_ozip=encrypted,
                        metadata=z.read('META-INF/com/android/metadata').decode(),
                        transfer_list=z.read('vendor.transfer.list').decode())
            with z.open('vendor.new.dat.br') as member:
                fact['vendor_member_header_hex'] = member.read(32).hex()
            (PRIVATE/('vendor-'+tag+'.transfer.list')).write_text(fact['transfer_list'])
        facts.append(fact)
        print(json.dumps(dict(package=tag, metadata_read=True, vendor_member_read=True)),flush=True)
    write('package-metadata-private.json', facts)

def vendor(tag):
    """Reconstruct only the local vendor member, then enforce HAL SHA gate."""
    facts = json.loads((PRIVATE/'package-metadata-private.json').read_text())
    if tag=='infinity':
        fact=dict(tag=tag,path='/mnt/c/Users/cy122/Downloads/Project_Infinity-X-3.12-samurai-24.07.2026-0750-GAPPS-UNOFFICIAL.zip',framed_ozip=False)
    else:
        fact = next(f for f in facts if f['tag']==tag)
    path = Path(fact['path'])
    output = PRIVATE/('vendor-'+tag)
    output.mkdir(exist_ok=True)
    image = output/'vendor.img'
    proof = output/'reconstruction-private.json'
    if not proof.exists():
        assert not image.exists(), 'Do not overwrite an unfinished or prior image'
        reader = LocalOzip(path) if fact['framed_ozip'] else path
        with zipfile.ZipFile(reader) as z:
            lines = z.read('vendor.transfer.list').decode().splitlines()
            assert lines[:1]==['4'] and lines[2:4]==['0','0']
            ranges, affected, limit = [], 0, 0
            for line in lines[4:]:
                op, blockset = line.split()
                assert op in ['new','zero','erase']
                values = [int(n) for n in blockset.split(',')]
                assert values[0] == len(values)-1 and values[0]%2==0
                for i in range(1,len(values),2):
                    a,b = values[i:i+2]
                    assert 0<=a<b<=417792
                    limit = max(limit,b)
                    if op == 'new': ranges.append((a*4096,b*4096))
                    if op in ['new','zero']: affected += b-a
            (output/'transfer-summary-private.json').write_text(json.dumps(dict(affected=affected,declared=int(lines[1]),limit=limit),indent=2)+'\n')
            assert affected == int(lines[1]) and limit <= 417792
            expected = sum(b-a for a,b in ranges)
            dec, index, written, position = NativeBrotli(), 0, 0, ranges[0][0]
            print('Reconstruct local vendor '+tag,flush=True)
            with image.open('xb') as dst,z.open('vendor.new.dat.br') as src:
                dst.truncate(417792*4096)
                dst.seek(position)
                while compressed := src.read(1024*1024):
                    plain, offset = memoryview(dec.process(compressed)), 0
                    while offset < len(plain):
                        assert index < len(ranges)
                        count = min(len(plain)-offset,ranges[index][1]-position)
                        dst.write(plain[offset:offset+count])
                        position += count
                        written += count
                        offset += count
                        if position == ranges[index][1]:
                            index += 1
                            if index < len(ranges):
                                position = ranges[index][0]
                                dst.seek(position)
                assert dec.is_finished() and written==expected and index==len(ranges)
            with image.open('rb') as f:
                f.seek(1080)
                assert f.read(2)==b'\x53\xef'
            item = z.getinfo('vendor.new.dat.br')
            result = dict(package=tag, bytes=image.stat().st_size,new_bytes=written,
                          brotli_finished=True, zip_crc_checked=True,
                          transfer_sha256=hashlib.sha256(z.read('vendor.transfer.list')).hexdigest(),
                          vendor_member_crc32=f'{item.CRC:08x}',vendor_member_bytes=item.file_size,
                          readonly_package=True,only_vendor_reconstructed=True)
            proof.write_text(json.dumps(result,indent=2)+'\n')
    compare_image(tag,image,output)

def compare_image(tag,image,output):
    hal = output/'camera.qcom.so'
    if not hal.exists():
        result = subprocess.run(['debugfs','-R','dump -p /lib64/hw/camera.qcom.so '+str(hal),str(image)],capture_output=True)
        (output/'debugfs-hal-private.txt').write_bytes(result.stdout+result.stderr)
        assert result.returncode == 0 and hal.exists() and hal.read_bytes().startswith(b'\x7fELF')
    match = sha(hal)==TARGET_SHA
    comparison = dict(package=tag,hal_bytes=hal.stat().st_size,hal_sha256=sha(hal),target_sha256=TARGET_SHA,
                      matches_current_281=match,lib_or_table_accepted=False)
    if match:
        lib = output/'libhwconfigurationutil.so'
        if not lib.exists():
            result = subprocess.run(['debugfs','-R','dump -p /lib64/libhwconfigurationutil.so '+str(lib),str(image)],capture_output=True)
            (output/'debugfs-library-private.txt').write_bytes(result.stdout+result.stderr)
            assert result.returncode == 0 and lib.exists() and lib.read_bytes().startswith(b'\x7fELF')
        strings = [m.group().decode() for m in re.finditer(rb'[ -~]{5,}',lib.read_bytes())]
        (output/'library-strings-private.json').write_text(json.dumps(strings,indent=2)+'\n')
        comparison.update(library_bytes=lib.stat().st_size,library_sha256=sha(lib),lib_or_table_accepted=True)
    (output/'hal-comparison-private.json').write_text(json.dumps(comparison,indent=2)+'\n')
    print(json.dumps(comparison),flush=True)

def f14():
    source=Path('/mnt/e/123pan/X2PRO 9008资料/X20Pro_F14/vendor.img')
    output=PRIVATE/'vendor-f14'
    output.mkdir(exist_ok=True)
    with source.open('rb') as f:
        header=f.read(28)
    if struct.unpack_from('<I',header)[0]==0xed26ff3a:
        magic,major,minor,file_header,chunk_header,block_size,blocks,chunks,checksum=struct.unpack('<IHHHHIIII',header)
        assert major==1 and file_header>=28 and chunk_header>=12 and block_size==4096 and blocks<=500000
        image=output/'vendor.img'
        proof=output/'sparse-conversion-private.json'
        if not proof.exists():
            assert not image.exists()
            position=0
            with source.open('rb') as src,image.open('xb') as dst:
                dst.truncate(blocks*block_size)
                src.seek(file_header)
                for _ in range(chunks):
                    raw=src.read(chunk_header)
                    kind,reserved,count,total=struct.unpack_from('<HHII',raw)
                    length=count*block_size
                    assert position+length<=blocks*block_size
                    if kind==0xcac1:
                        assert total==chunk_header+length
                        remaining=length
                        while remaining:
                            part=src.read(min(1024*1024,remaining))
                            assert part
                            dst.write(part)
                            remaining-=len(part)
                    elif kind==0xcac2:
                        assert total==chunk_header+4
                        fill=src.read(4)
                        assert len(fill)==4
                        remaining=length
                        while remaining:
                            count_bytes=min(1024*1024,remaining)
                            dst.write(fill*(count_bytes//4))
                            remaining-=count_bytes
                    elif kind==0xcac3:
                        assert total==chunk_header
                        dst.seek(length,1)
                    elif kind==0xcac4:
                        assert total==chunk_header+4 and count==0
                        assert len(src.read(4))==4
                    else:
                        raise AssertionError('Unknown Android sparse chunk')
                    position+=length
                assert position==blocks*block_size and not src.read(1)
            with image.open('rb') as f:
                f.seek(1080)
                assert f.read(2)==b'\x53\xef'
            proof.write_text(json.dumps(dict(source=str(source),source_bytes=source.stat().st_size,
                                            image_bytes=image.stat().st_size,chunks=chunks,block_size=block_size,
                                            source_readonly=True,ext4_magic=True),indent=2)+'\n')
    else:
        image=source
    compare_image('f14',image,output)

def additional_packages():
    reports=[]
    for path in [Path('/mnt/e/123pan/X2PRO 9008资料/X20Pro_F14.zip'),
                 Path('/mnt/c/Users/cy122/Downloads/Project_Infinity-X-3.12-samurai-24.07.2026-0750-GAPPS-UNOFFICIAL.zip')]:
        with zipfile.ZipFile(path) as z:
            report=dict(path=str(path),bytes=path.stat().st_size,
                        members=[dict(path=i.filename,bytes=i.file_size,crc32=f'{i.CRC:08x}') for i in z.infolist()],
                        metadata=z.read('META-INF/com/android/metadata').decode() if 'META-INF/com/android/metadata' in z.namelist() else None)
            probes=[]
            for i in z.infolist():
                if re.search('(?i)vendor|payload',i.filename):
                    z.fp.seek(i.header_offset)
                    probes.append(dict(path=i.filename,offset=i.header_offset,magic=z.fp.read(4).hex()))
            report['local_header_probes']=probes
        reports.append(report)
        print(json.dumps(dict(package=path.name,relevant=[i for i in report['members'] if re.search('(?i)vendor|payload|camera.qcom|hwconfiguration',i['path'])])),flush=True)
    write('additional-package-inventory-private.json',reports)

def retained_inventories():
    reports=[]
    for stage in [115,251,257,281,326]:
        root=P/('kernel'+str(stage))
        for path in sorted(root.iterdir()):
            if not path.is_file() or not re.search(r'\.(?:tar|tar\.gz|tgz)$',path.name):
                continue
            relevant=[]
            members=0
            complete=True
            error=None
            try:
                with tarfile.open(path) as t:
                    for member in t:
                        members+=1
                        if re.search(r'(?i)(camera\.qcom\.so|libhwconfigurationutil\.so|OemCamActuatorSettingMap)|(?:F[._]?16|RMX1931).*\.(?:zip|ozip|ofp)$',member.name):
                            relevant.append(dict(path=member.name,bytes=member.size))
            except (tarfile.ReadError,EOFError) as failure:
                complete=False
                error=type(failure).__name__+': '+str(failure)
            reports.append(dict(archive=str(path),bytes=path.stat().st_size,members=members,relevant=relevant,complete=complete,error=error))
    write('retained-archive-inventory-private.json',reports)
    print(json.dumps(dict(archives=len(reports),matching_members=sum(len(r['relevant']) for r in reports))),flush=True)

def summarize():
    assert sha(P/'kernel281/camera.qcom.so-private')==TARGET_SHA
    baseline=json.loads((PRIVATE/'stable-inputs-private.json').read_text())
    assert baseline=={name:sha(HERE/name) for name in STABLE}
    candidates=[]
    for tag in ['1330','1340','f14']:
        root=PRIVATE/('vendor-'+tag)
        comparison=json.loads((root/'hal-comparison-private.json').read_text())
        assert sha(root/'camera.qcom.so')==comparison['hal_sha256']
        assert not comparison['matches_current_281'] and not comparison['lib_or_table_accepted']
        assert not (root/'libhwconfigurationutil.so').exists()
        if tag in ['1330','1340']:
            proof=json.loads((root/'reconstruction-private.json').read_text())
            assert proof['brotli_finished'] and proof['zip_crc_checked'] and proof['only_vendor_reconstructed']
        else:
            proof=json.loads((root/'sparse-conversion-private.json').read_text())
            assert proof['source_readonly'] and proof['ext4_magic']
        candidates.append(dict(source=tag,hal_bytes=comparison['hal_bytes'],hal_sha256=comparison['hal_sha256'],
                               matches_281=False,library_accepted=False))
    reused_path=P/'kernel453/af-individual/vendor-authority/hal-image-comparison-private.json'
    reused=json.loads(reused_path.read_text())
    assert len(reused)==2 and all(not r['matches_retained_current_hal'] and r['debugfs_readonly'] for r in reused)
    archives=json.loads((PRIVATE/'retained-archive-inventory-private.json').read_text())
    assert not any(a['relevant'] for a in archives)
    repos=json.loads((PRIVATE/'cached-repositories-private.json').read_text())
    repo_summary=[]
    for repo in repos:
        hal=next(i for i in repo['selected'] if i['path'].endswith('/lib64/hw/camera.qcom.so'))
        assert not hal['matches_281_hal']
        repo_summary.append(dict(commit=repo['commit'],hal_bytes=hal['bytes'],hal_sha256=hal['sha256'],
                                 lfs_pointer=hal['lfs_pointer'],matches_281=False))
    additional=json.loads((PRIVATE/'additional-package-inventory-private.json').read_text())
    infinity=next(i for i in additional if 'Infinity' in i['path'])
    vendor_probe=next(p for p in infinity['local_header_probes'] if p['path']=='vendor.new.dat.br')
    assert vendor_probe['magic']!='504b0304'
    result=dict(stage=453,task='matching AF configuration source search',
                current_hal=dict(bytes=(P/'kernel281/camera.qcom.so-private').stat().st_size,sha256=TARGET_SHA),
                historical_build_context='251: RMX1931_11_F.16; 257: return to Linux; identity authority remains exact 281 HAL SHA',
                local_vendor_candidates=candidates,cached_repository_candidates=repo_summary,
                reused_242_248_evidence=dict(sha256=sha(reused_path),hal_sha256=reused[0]['sha256'],reextracted=False),
                retained_archives=dict(total=len(archives),complete=sum(a['complete'] for a in archives),
                                       partial=sum(not a['complete'] for a in archives),matching_observed_members=0,
                                       partial_archive_not_proof_of_absence=True),
                additional_local_zip=dict(vendor_member_local_header_valid=False,vendor_reconstruction_accepted=False),
                matching_library_found=False,configuration_backing_path_known=False,table_parsed=False,
                external_override_selection_known=False,previous_af_files_unchanged=baseline,
                no_phone=True,no_ssh=True,no_sdk=True,no_build=True,no_network=True,
                existing_candidates_modified=False,formal_configuration_modified=False,
                checker_sha256=sha(Path(__file__)),report_sha256=sha(HERE/'AF-CONFIG-SOURCE.md'),
                temporary_vendor_images_absent=all(not (PRIVATE/('vendor-'+tag)/'vendor.img').exists() for tag in ['1330','1340','f14','infinity']),
                private_directory='E:/edk2-samurai-out/kernel453/af-config-source/',
                conclusion='No matching local authority found in the enumerated sources; retain conditional individual candidate without modification')
    (HERE/'af-config-source-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(matching_library_found=False,table_parsed=False,previous_six_files_unchanged=True,
                         local_vendor_candidates=len(candidates),cached_repositories=len(repo_summary))),flush=True)

def cleanup_images():
    """Drop only this task's reconstructible image outputs, preserving proofs."""
    removed=[]
    for tag in ['1330','1340','f14','infinity']:
        root=PRIVATE/('vendor-'+tag)
        image=root/'vendor.img'
        if not image.exists(): continue
        assert image.resolve().parent==root.resolve() and root.resolve().parent==PRIVATE.resolve()
        if tag!='infinity':
            comparison=json.loads((root/'hal-comparison-private.json').read_text())
            assert not comparison['matches_current_281'] and not comparison['lib_or_table_accepted']
            assert sha(root/'camera.qcom.so')==comparison['hal_sha256']
        else:
            with image.open('rb') as f:
                assert image.stat().st_size==0 or f.read(4096)==bytes(4096)
            assert not (root/'reconstruction-private.json').exists()
        removed.append(dict(path=str(image),logical_bytes=image.stat().st_size))
        image.unlink()
    write('temporary-image-cleanup-private.json',dict(removed_this_call=removed,
          final_state=[dict(package=tag,image_exists=(PRIVATE/('vendor-'+tag)/'vendor.img').exists()) for tag in ['1330','1340','f14','infinity']],
          source_packages_untouched=True,hal_proofs_retained=True))
    print(json.dumps(dict(removed_images=len(removed),source_packages_untouched=True)),flush=True)

def runtime():
    print('Inspector python '+sys.executable,flush=True)
    import ctypes.util
    print('brotlidec '+str(ctypes.util.find_library('brotlidec')),flush=True)
    header=Path('/usr/include/brotli/decode.h')
    if header.exists():
        (PRIVATE/'brotli-decode-header-private.h').write_bytes(header.read_bytes())
    for executable in ['/usr/bin/python3','/usr/local/bin/python3','/home/cy122/x2pro-linux/.venv/bin/python']:
        if Path(executable).exists():
            r = subprocess.run([executable,'-c','import sys,importlib.util,json; print(json.dumps(dict(python=sys.executable,brotli=importlib.util.find_spec("brotli") is not None,Crypto=importlib.util.find_spec("Crypto") is not None)))'],capture_output=True,text=True)
            print(r.stdout.strip(),r.stderr.strip(),flush=True)

def cached_repos():
    reports=[]
    for name,commit in [('vendor-c38-reference-git-private','0ef1fc05360421845f1ae905852dbfe63b26ba68'),
                        ('vendor-lineage18-reference-git-private','b94e26044cb95092add5dd8026fab0fdcb61433a')]:
        repo=P/'kernel113'/name
        assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip()==commit
        paths=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',commit]).decode().splitlines()
        chosen=[p for p in paths if re.search(r'(?i)(camera\.qcom\.so|libhwconfigurationutil\.so|hwconfig|configuration|oemcam)',p)]
        selected=[]
        for path in chosen:
            blob=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+path])
            m=re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (\d+)\n',blob)
            item=dict(path=path,git_blob_bytes=len(blob),lfs_pointer=bool(m))
            if m:
                digest,size=m[1].decode(),int(m[2])
                cached=repo/'.git/lfs/objects'/digest[:2]/digest[2:4]/digest
                item.update(sha256=digest,bytes=size,cached_object=cached.exists(),matches_281_hal=digest==TARGET_SHA)
            else:
                item.update(sha256=hashlib.sha256(blob).hexdigest(),bytes=len(blob),matches_281_hal=hashlib.sha256(blob).hexdigest()==TARGET_SHA)
            selected.append(item)
        reports.append(dict(repo=str(repo),commit=commit,selected=selected))
        print(json.dumps(dict(cached_repo_checked=name,selected=selected)),flush=True)
    write('cached-repositories-private.json',reports)

def inventory():
    assert sha(P/'kernel281/camera.qcom.so-private') == TARGET_SHA
    archives = []
    for name in ['camera-config-list-private.tar.gz', 'vendor-camera-source-private.tar.gz']:
        archive = P/'kernel115'/name
        with tarfile.open(archive) as t:
            members = []
            for m in t.getmembers():
                item = dict(name=m.name, size=m.size)
                if m.isfile() and m.size < 256*1024 and m.name.endswith(('.txt', '.sha256', 'SHA256SUMS')):
                    data = t.extractfile(m).read()
                    item['text'] = data.decode(errors='replace')
                members.append(item)
        archives.append(dict(path=str(archive), sha256=sha(archive), members=members))
    write('k115-listing-private.json', archives)
    roots = [Path('/mnt/e/RMX1931_decrypted'), Path('/mnt/e/RMX1931_ozip_extract'),
             Path('/mnt/e/系统rom'), Path('/mnt/c/Users/cy122/Downloads')]
    packages = [Path('/mnt/e/RMX1931_11_OTA_1340_all_2QCxQYdkxpql.ozip')]
    for root in roots:
        if root.exists():
            for folder, dirs, files in os.walk(root):
                if root.name == 'Downloads':
                    dirs[:] = []  # Known package cache is the root; avoid unrelated downloads.
                for name in files:
                    if re.search(r'(?i)(RMX1931|crDroid).*\.(zip|ozip|ofp)$|(?:camera\.qcom|libhwconfigurationutil)\.so$|vendor.*\.(img|dat|br)$', name):
                        packages.append(Path(folder)/name)
    facts = []
    for path in dict.fromkeys(packages):
        print('Inventory '+str(path), flush=True)
        fact = dict(path=str(path), exists=path.exists())
        if path.exists():
            fact['bytes'] = path.stat().st_size
            with path.open('rb') as f:
                fact['header_hex'] = f.read(32).hex()
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path) as z:
                    relevant = [dict(name=i.filename, bytes=i.file_size, compressed=i.compress_size,
                                     crc32=f'{i.CRC:08x}', flags=i.flag_bits, method=i.compress_type)
                                for i in z.infolist() if re.search(r'(?i)(vendor|camera|hwconfig|metadata|build\.prop)', i.filename)]
                    fact['zip_relevant_members'] = relevant
        facts.append(fact)
    write('local-package-inventory-private.json', facts)
    stable={name:sha(HERE/name) for name in STABLE}
    if (PRIVATE/'stable-inputs-private.json').exists():
        assert json.loads((PRIVATE/'stable-inputs-private.json').read_text())==stable
    else:
        write('stable-inputs-private.json', stable)
    print(json.dumps(dict(listing_archives=len(archives), package_candidates=len(facts),
                         existing_packages=sum(f['exists'] for f in facts), target_hal_verified=True)))

if __name__ == '__main__':
    if sys.argv[1:] == ['--inventory']:
        inventory()
    elif sys.argv[1:] == ['--packages']:
        packages()
    elif len(sys.argv)==3 and sys.argv[1]=='--vendor' and sys.argv[2] in ['1330','1340','infinity']:
        vendor(sys.argv[2])
    elif sys.argv[1:]==['--runtime']:
        runtime()
    elif sys.argv[1:]==['--cached-repos']:
        cached_repos()
    elif sys.argv[1:]==['--f14']:
        f14()
    elif sys.argv[1:]==['--additional-packages']:
        additional_packages()
    elif sys.argv[1:]==['--retained-inventories']:
        retained_inventories()
    elif sys.argv[1:]==['--summarize']:
        summarize()
    elif sys.argv[1:]==['--cleanup-images']:
        cleanup_images()
    else:
        raise SystemExit('Use --inventory, --packages, --vendor {1330,1340,infinity}, --f14, --cached-repos, --additional-packages, --retained-inventories, --summarize, or --cleanup-images')
