"""Default check-local only. One separately approved private two-FFS build; never deploys."""
from pathlib import Path
import hashlib,importlib.util,json,lzma,os,re,shutil,stat,struct,subprocess,sys,traceback,zlib
sys.dont_write_bytecode=True # check-local must remain read-only even without python -B

HERE=Path(__file__).resolve().parent
REF=HERE.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
helper=REF/'eud-boot-packaging-review/baseline-draft.py'
assert sha(helper.read_bytes())=='255e73c69eee98da87dea022e2347ccddff743d471a2b9fce2dc30c301a4e708'
spec=importlib.util.spec_from_file_location('sealed_a30_helpers',helper)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base) # definitions only
m=base.m;fv=base.fv;sections=base.sections;align=base.align
ROOT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
COMPACT=ROOT/'eud-boot-compact-baseline-private-01'
GZIP=ROOT/'eud-boot-gzip-baseline-private-01'
OUT=ROOT/'eud-boot-two-ffs-candidate-private-01'
BDS='6d33944a-ec75-4855-a54d-809c75241f6c';DT='25462cda-221f-47df-ac1d-259cfaa4e326'
SEC='8af09f13-44c5-96ec-1437-dd899cb5ee5d';CONTAINER='9e21fd93-9c72-4c15-8c4b-e77f1db2d792'
LIMIT=6686720;PARTITION=100663296
TOOLS={Path(t['path']).name:t['path'] for t in m['tools']}
EFI=Path(m['candidate_EFI']['path']);DTB=Path(m['candidate_native_DTB']['path'])
def read_pinned(path,digest):
    raw=path.read_bytes();assert sha(raw)==digest,str(path)+' hash differs';return raw
compact_receipt=json.loads(read_pinned(COMPACT/'result.json','c81ae504e6bf89253dea83a0f5a6831dd7084ade73ab23d45d22f976c9c1467b'))
gzip_receipt=json.loads(read_pinned(GZIP/'result.json','3de516c86a7ca1d2fcb6069741aa253c7470f844bd2e809d6969ceb1f9733632'))
assert compact_receipt['passed'] and compact_receipt['full_FD_byte_equal']
assert gzip_receipt['passed'] and gzip_receipt['gzip_byte_equal_a30'] and gzip_receipt['payload_byte_equal_a30']
def raw_files(volume):
    fv(volume) # existing parser validates FV/FFS header/data checksums and sections
    files={};offset=align(struct.unpack_from('<H',volume,48)[0],8)
    while offset+24<=len(volume) and volume[offset:offset+24]!=b'\xff'*24:
        size=int.from_bytes(volume[offset+20:offset+23],'little')
        if volume[offset+19]&1:size=struct.unpack_from('<Q',volume,offset+24)[0]
        full=volume[offset:offset+size]
        if full[18]!=0xf0:
            import uuid
            guid=str(uuid.UUID(bytes_le=full[:16]));assert guid not in files
            files[guid]={'offset':offset,'full':full}
        offset=align(offset+size,8)
    return files
def id_value(payload,ramdisk):
    h=hashlib.sha1()
    for raw in [payload,ramdisk]:h.update(raw);h.update(struct.pack('<I',len(raw)))
    h.update(struct.pack('<II',0,0));return h.digest()+b'\0'*12
def snapshot(paths):return {str(p):sha(p.read_bytes()) for p in sorted(paths)}
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def check_local():
    old=base.unpack() # actual a30, original Android ID verified before any tool
    assert len(old['boot'])==PARTITION and sha(old['boot'])=='a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280'
    old_ks=struct.unpack_from('<I',old['boot'],8)[0];old_ram=2048+align(old_ks,2048)
    assert old_ram+2048==LIMIT and old['boot'][old_ram:old_ram+1]==b'\n'
    assert old['boot'][2048+old_ks:old_ram]==b'\0'*(old_ram-2048-old_ks)
    assert old['boot'][576:608]==id_value(old['payload'],b'\n')
    read_pinned(EFI,'a0e30c69b91f5605c07136f3f0c6900434f99d72159c5c61ac01db47fc061768')
    read_pinned(DTB,'9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358')
    read_pinned(COMPACT/'compact.fd',m['saved_compact_FD']['sha256'])
    for tool in m['tools']:read_pinned(Path(tool['path']),tool['sha256'])
    before=snapshot({Path(p) for p in gzip_receipt['inputs_before']})
    assert before==gzip_receipt['inputs_before'],'frozen baseline parent inputs changed'
    assert len(raw_files(old['main']))==101
    assert [s[0] for s in fv(old['main'])[BDS]['sections']]==[0x13,0x10,0x15]
    assert [s[0] for s in fv(old['main'])[DT]['sections']]==[0x19]
    return old,old_ram
def verify_main(main,old):
    a,b=raw_files(old['main']),raw_files(main);assert list(a)==list(b) and len(b)==101
    changed=[g for g in a if a[g]['full']!=b[g]['full']]
    assert set(changed)=={BDS,DT} and len(changed)==2,'only BDS and native-DTB FFS may change'
    assert all(a[g]['full']==b[g]['full'] for g in a if g not in {BDS,DT})
    oldmods,newmods=fv(old['main']),fv(main)
    for g in a:assert (oldmods[g]['type'],oldmods[g]['attrs'])==(newmods[g]['type'],newmods[g]['attrs'])
    bs=newmods[BDS]['sections'];previous=oldmods[BDS]['sections']
    assert [s[0] for s in bs]==[0x13,0x10,0x15]
    assert bs[0][2]==previous[0][2] and bs[2][2]==previous[2][2]
    assert bs[1][1]==EFI.read_bytes(),'frozen EFI must be exact, without artificial padding'
    ds=newmods[DT]['sections'];assert len(ds)==1 and ds[0][0]==0x19 and ds[0][1]==DTB.read_bytes()
    return {'changed_FFS':changed,'unchanged_complete_FFS_count':99,'BDS_depex_UI_preserved':True,'EFI_DTB_payloads_exact':True}
def decode_boot(blob):
    assert blob[:8]==b'ANDROID!' and len(blob)==PARTITION
    ks,rs,ss,page,version=[struct.unpack_from('<I',blob,p)[0] for p in [8,16,24,36,40]]
    assert (rs,ss,page,version)==(1,0,2048,1)
    used=page+align(ks,page)+align(rs,page);assert used<=LIMIT
    payload=blob[page:page+ks];d=zlib.decompressobj(31);raw=d.decompress(payload)+d.flush()
    assert d.eof and not d.unconsumed_tail and d.unused_data==base.unpack()['compat']
    ram=page+align(ks,page);assert blob[576:608]==id_value(payload,blob[ram:ram+rs])
    assert len(raw)==7340176
    fd=raw[144:];outer=fv(fd);image=[v for v in outer.values() if v['type']==0xb]
    assert len(image)==1 and len(image[0]['sections'])==1
    typ,body,section=image[0]['sections'][0]
    assert typ==2 and str(__import__('uuid').UUID(bytes_le=body[:16]))==m['compression']['guided_guid']
    offset,attrs=struct.unpack_from('<HH',body,16);assert (offset,attrs)==(24,1)
    nested=sections(lzma.decompress(section[offset:],format=lzma.FORMAT_ALONE))
    assert len(nested)==1 and nested[0][0]==0x17
    return {'ks':ks,'used':used,'ram_offset':ram,'raw':raw,'fd':fd,'main':nested[0][1]}
def execute():
    assert not OUT.exists(),'unique private directory exists; never replay'
    old,old_ram=check_local()
    paths={Path(p) for p in gzip_receipt['inputs_before']}
    paths.update([helper,COMPACT/'result.json',COMPACT/'compact.fd',GZIP/'result.json',EFI,DTB,Path(__file__)])
    for ext in ['.ffs','.efi','.map']:paths.add(COMPACT/'inputs'/(SEC.upper()+ext))
    before=snapshot(paths);mount_before=Path('/proc/self/mountinfo').read_bytes()
    OUT.mkdir(parents=True);(OUT/'inputs').mkdir();(OUT/'sections').mkdir()
    result={'passed':False,'scope':'unflashed private two-FFS candidate only','host_linux_pid':os.getpid(),
            'rollback_a30_sha256':sha(old['boot']),'EFI_sha256':sha(EFI.read_bytes()),'DTB_sha256':sha(DTB.read_bytes()),
            'commands':[],'inputs_before':before,'old_Android_ID_verified_before_tools':True}
    print(json.dumps({'started':True,'host_linux_pid':os.getpid(),'private_directory':str(OUT)}),flush=True)
    def tool(name,args,stage,stdin=None,stdout=None):
        argv=[TOOLS[name]]+[str(v) for v in args]
        entry={'stage':stage,'argv':argv};result['commands'].append(entry);save(OUT/'result.json',result)
        env=dict(os.environ,PATH='/usr/bin:/bin');env.pop('GZIP',None)
        with (OUT/(stage+'.stderr')).open('wb') as err:
            if stdin is not None:
                with Path(stdin).open('rb') as source,Path(stdout).open('wb') as output:
                    st=os.fstat(source.fileno());assert stat.S_ISREG(st.st_mode)
                    entry['stdin_fstat']={'regular':True,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'device':st.st_dev,'inode':st.st_ino}
                    assert st.st_size==7340176 and st.st_mtime_ns==1792719172000000000
                    done=subprocess.run(argv,stdin=source,stdout=output,stderr=err,cwd=OUT,env=env,timeout=120)
            else:
                with (OUT/(stage+'.stdout')).open('wb') as output:done=subprocess.run(argv,stdout=output,stderr=err,cwd=OUT,env=env,timeout=120)
        entry['returncode']=done.returncode;save(OUT/'result.json',result);assert done.returncode==0,stage+' failed'
    try:
        inputs=base.extract(old['main'],m['main_FV']['files'],OUT/'inputs')
        for g in [BDS,DT]:shutil.copy2(inputs[g],OUT/('original-'+g+'.ffs'))
        mods=fv(old['main']);(OUT/'sections/BDS.dpx').write_bytes(mods[BDS]['sections'][0][2]);(OUT/'sections/BDS.ui').write_bytes(mods[BDS]['sections'][2][2])
        tool('GenSec',['-s','EFI_SECTION_PE32','-o',OUT/'sections/BDS.pe32',EFI],'BDS-PE32')
        tool('GenFfs',['-t','EFI_FV_FILETYPE_DRIVER','-g',BDS,'-o',inputs[BDS],'-oi',OUT/'sections/BDS.dpx','-oi',OUT/'sections/BDS.pe32','-oi',OUT/'sections/BDS.ui'],'BDS-FFS')
        tool('GenSec',['-s','EFI_SECTION_RAW','-o',OUT/'sections/DTB.raw',DTB],'DTB-RAW')
        tool('GenFfs',['-t','EFI_FV_FILETYPE_FREEFORM','-g',DT,'-o',inputs[DT],'-i',OUT/'sections/DTB.raw'],'DTB-FFS')
        base.inf(m['main_config']['config'],[inputs[i['guid']] for i in m['main_FV']['files']],OUT/'FVMAIN.inf')
        tool('GenFv',['-g',m['main_FV']['filesystem_guid'],'-i',OUT/'FVMAIN.inf','-o',OUT/'main.Fv'],'mainFV')
        result['main_verification']=verify_main((OUT/'main.Fv').read_bytes(),old)
        tool('GenSec',['-s','EFI_SECTION_FIRMWARE_VOLUME_IMAGE','-o',OUT/'main.fv.sec',OUT/'main.Fv'],'FV-IMAGE')
        tool('GenSec',['--sectionalign','8','-o',OUT/'main.aligned',OUT/'main.fv.sec'],'align8')
        tool('LzmaCompress',['-e','-o',OUT/'main.lzma',OUT/'main.aligned'],'LZMA')
        tool('GenSec',['-s','EFI_SECTION_GUID_DEFINED','-g',m['compression']['guided_guid'],'-r','PROCESSING_REQUIRED','-o',OUT/'main.guided',OUT/'main.lzma'],'GUIDED')
        tool('GenFfs',['-t','EFI_FV_FILETYPE_FIRMWARE_VOLUME_IMAGE','-g',CONTAINER,'-o',OUT/'container.ffs','-i',OUT/'main.guided'],'containerFFS')
        for ext in ['.ffs','.efi','.map']:shutil.copy2(COMPACT/'inputs'/(SEC.upper()+ext),OUT/'inputs'/(SEC.upper()+ext))
        base.inf(m['compact_config']['config'],[OUT/'inputs'/(SEC.upper()+'.ffs'),OUT/'container.ffs'],OUT/'FVMAIN_COMPACT.inf')
        tool('GenFv',['-g',m['compact_FV']['filesystem_guid'],'-i',OUT/'FVMAIN_COMPACT.inf','-o',OUT/'compact.fd'],'compactFD')
        fd=(OUT/'compact.fd').read_bytes();a,b=raw_files(old['fd']),raw_files(fd)
        assert len(fd)==7340032 and list(a)==list(b)==[SEC,CONTAINER]
        assert b[SEC]['offset']==a[SEC]['offset']==0xfe8 and b[SEC]['full']==a[SEC]['full']
        assert b[CONTAINER]['offset']==a[CONTAINER]['offset']
        header_len=struct.unpack_from('<H',fd,48)[0];assert fd[:header_len]==old['fd'][:header_len]
        raw=old['shim']+fd;assert len(raw)==7340176
        (OUT/'raw.bin').write_bytes(raw);os.utime(OUT/'raw.bin',ns=(1792719172000000000,1792719172000000000))
        tool('gzip',['-c'],'gzip',stdin=OUT/'raw.bin',stdout=OUT/'raw.gz')
        gz=(OUT/'raw.gz').read_bytes();assert gz[:10]==old['gzip'][:10]
        payload=gz+old['compat'];ks=len(payload);new_ram=2048+align(ks,2048);used=new_ram+2048
        result['new_kernel_size']=ks;result['new_used']=used
        assert used<=LIMIT,'new used bytes would overwrite nonzero a30 tail; stop without boot output'
        header=bytearray(old['boot'][:2048]);header[8:12]=struct.pack('<I',ks);header[576:608]=id_value(payload,b'\n')
        ram_page=old['boot'][old_ram:old_ram+2048]
        prefix=bytes(header)+payload+b'\0'*(new_ram-2048-ks)+ram_page;assert len(prefix)==used
        candidate=prefix+old['boot'][used:];assert len(candidate)==PARTITION
        target=OUT/'boot-two-ffs-private.img'
        with target.open('xb') as out:out.write(candidate);out.flush();os.fsync(out.fileno())
        readback=target.read_bytes();assert readback==candidate
        parsed=decode_boot(readback)
        assert parsed['raw'][:144]==old['shim'] and parsed['fd']==fd and parsed['main']==(OUT/'main.Fv').read_bytes()
        result['written_main_verification']=verify_main(parsed['main'],old)
        h=bytearray(readback[:2048]);original_h=bytearray(old['boot'][:2048])
        for x in [h,original_h]:x[8:12]=b'\0'*4;x[576:608]=b'\0'*32
        assert h==original_h,'Android header changed outside kernel_size/ID'
        assert readback[parsed['ram_offset']:parsed['used']]==ram_page
        assert readback[used:]==old['boot'][used:] and readback[LIMIT:]==old['boot'][LIMIT:]
        result.update(passed=True,boot_path=str(target),boot_bytes=len(readback),boot_sha256=sha(readback),
                      SEC_full_FFS_preserved=True,SEC_offset=0xfe8,shim_compat_ramdisk_preserved=True,
                      tail_absolute_preserved=True,header_only_size_ID_changed=True,written_boot_fully_reparsed=True,
                      external_Image_untouched=True,no_deployment_or_device_access=True)
    except BaseException as exc:result['error']=repr(exc);result['traceback']=traceback.format_exc()
    finally:
        result['inputs_after']=snapshot(paths);result['parent_inputs_unchanged']=before==result['inputs_after']
        result['parent_mountinfo_unchanged']=mount_before==Path('/proc/self/mountinfo').read_bytes()
        result['passed'] &= result['parent_inputs_unchanged'] and result['parent_mountinfo_unchanged']
        result['artifacts']={p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.is_file() and p.name!='result.json'}
        save(OUT/'result.json',result)
        public={k:v for k,v in result.items() if k not in ['inputs_before','inputs_after','traceback','commands','artifacts']}
        public['commands_sha256']=sha(json.dumps(result['commands'],sort_keys=True).encode())
        public['private_result_sha256']=sha((OUT/'result.json').read_bytes());save(HERE/'result.json',public);print(json.dumps(public,indent=2))
    return 0 if result['passed'] else 1
if __name__=='__main__':
    if sys.argv[1:] in [[],['--check-local']]:
        check_local();print(json.dumps({'checked':True,'tools_executed':False,'candidate_directory_exists':OUT.exists(),'allowed_changed_FFS':[BDS,DT],'remaining_complete_FFS':99,'max_used':LIMIT}))
    elif sys.argv[1:]==['--execute-two-ffs']:raise SystemExit(execute())
    else:raise SystemExit('default --check-local; --execute-two-ffs requires separate root review/approval')
