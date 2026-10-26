"""Only privately replace current Image501 FAT /Image with frozen Image502. Default is read-only; never deploys."""
from pathlib import Path
import hashlib,io,json,os,shutil,struct,subprocess,sys,traceback
sys.dont_write_bytecode=True
if sys.flags.optimize: raise RuntimeError("Non-optimized interpreter required")
HERE=Path(__file__).resolve().parent
ROOT=Path('/mnt/e/edk2-samurai-out')
OLD=ROOT/'charging-management-20261023/gauge-image501-logdump-private-01/logdump-gauge501-private.img'
IMAGE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01/build/arch/arm64/boot/Image')
OUT=ROOT/'charging-management-20261023/gauge-image502-logdump-private-01'
sha=lambda b:hashlib.sha256(b).hexdigest()
TOOLS={'mcopy':('/usr/bin/mcopy','ff7249e732c43e4f00716fdd1f50515e012d51c38f536d18e1e25bf57f372f8c'),
       'fsck.fat':('/usr/sbin/fsck.fat','4e2aa9699ac6a103b8d27e1c0bceb8f8e6a817ff067f97cb240918e5aa75ae5c')}
def read_bytes(p):
    # DrvFS large single read returned ENOMEM; keep identical bytes semantics.
    with p.open('rb') as source, io.BytesIO() as output:
        while chunk := source.read(1024*1024):
            output.write(chunk)
        return output.getvalue()

def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def pinned(p,d):
    b=read_bytes(p);assert sha(b)==d,str(p)+' differs';return b
def parse_fat(b):
    # Exact existing ACA FAT16 geometry and small root-only directory, not a formatter.
    assert len(b)==67108864 and b[510:512]==b'\x55\xaa'
    bps=struct.unpack_from('<H',b,11)[0];spc=b[13];reserved=struct.unpack_from('<H',b,14)[0]
    fats=b[16];roots=struct.unpack_from('<H',b,17)[0];spf=struct.unpack_from('<H',b,22)[0]
    assert (bps,spc,reserved,fats,roots,spf)==(4096,1,1,2,512,8)
    fat_at=reserved*bps;fat_size=spf*bps;root_at=(reserved+fats*spf)*bps
    root_size=roots*32;data_at=root_at+root_size;cluster_count=(len(b)-data_at)//bps
    fat=b[fat_at:fat_at+fat_size];assert fat==b[fat_at+fat_size:fat_at+2*fat_size]
    def chain(first):
        seen=[];visited=set();n=first
        while n<0xfff8:
            assert 2<=n<cluster_count+2 and n not in visited
            seen.append(n);visited.add(n);n=struct.unpack_from('<H',fat,n*2)[0]
        return seen
    files={};lfn=[];group=[]
    for at in range(root_at,root_at+root_size,32):
        e=b[at:at+32]
        if e[0]==0:break
        if e[0]==0xe5:lfn=[];group=[];continue
        if e[11]==0xf:lfn.append(e);group.append(at);continue
        if e[11]&8:assert not lfn;group=[];continue # unchanged volume label
        assert not e[11]&0x10,'only known root files accepted'
        if lfn:
            assert len(lfn)==1 and lfn[0][0]==0x41
            ch=lfn[0][1:11]+lfn[0][14:26]+lfn[0][28:32]
            name=ch.decode('utf-16-le').split('\0',1)[0]
            assert name=='Image'
        else:
            a=e[:8].decode().rstrip();ext=e[8:11].decode().rstrip();name=a+('.'+ext if ext else '')
        assert name not in files
        size=struct.unpack_from('<I',e,28)[0];first=struct.unpack_from('<H',e,26)[0]
        clusters=chain(first);assert len(clusters)==(size+bps-1)//bps
        content=b''.join(b[data_at+(n-2)*bps:data_at+(n-1)*bps] for n in clusters)[:size]
        files[name]={'entry_offsets':group+[at],'entries':b''.join(b[o:o+32] for o in group+[at]),
                     'clusters':clusters,'content':content,'size':size,'sha256':sha(content)}
        lfn=[];group=[]
    assert set(files)=={'Image','SAMURAI.DTB'} and not lfn
    assert not set(files['Image']['clusters']) & set(files['SAMURAI.DTB']['clusters'])
    return {'bps':bps,'fat_at':fat_at,'fat_size':fat_size,'data_at':data_at,'files':files}
def load_502_proof():
    # No Image access until an explicit frozen author handoff and all receipts.
    pins=json.loads(read_bytes(HERE / 'Image502-pins.json'))
    if not pins.get('ready'):
        return None
    leaf=HERE.parents[1]/'charging-ui-audit-20261023/gauge-image502-notify-candidate'
    delivery=json.loads(pinned(leaf/'delivery.json',pins['delivery_sha256']))
    records={}
    for name in ['build-result.json','abi-reuse-result.json','execution-receipt.json']:
        digest=pins['receipts'][name]
        assert delivery['files'][name]==digest
        records[name]=json.loads(pinned(leaf/name,digest))
    r=records['build-result.json'];a=records['abi-reuse-result.json'];e=records['execution-receipt.json']
    assert delivery['passed'] and r['passed'] and a['passed'] and e['passed']
    assert r['child_returncode']==0 and r['child_state']['terminal'] and r['child_state']['returncode']==0
    assert r['parent_namespace_unchanged'] and r['parent_mounts_unchanged']
    assert r['shared_before']==r['shared_after'] and r['original363_before']==r['original363_after']
    assert all(r['baseline_trees_preserved'].values())
    assert r['B_source_sha256']==delivery['source_sha256']=='0014077792948460fc2a2e9581225dc684cba4d5bff95c3e88767d661ce5439b'
    build=r['build'];compat=build['compatibility']
    assert build['passed'] and compat['passed'] and build['B_default_false_unchanged']
    assert build['unchanged_other_leaf_count']==3245 and build['unchanged_libstub_count']==32
    assert [x['path'] for x in build['leaf_delta']]==['drivers/power/supply/bq27xxx_battery.o','init/version.o']
    assert build['initramfs_unchanged'] and build['config_exact_original'] and build['release_unchanged']
    assert compat['actual_ELF_export_names_exact_501'] and compat['builtin_export_rows_exact_501']
    assert compat['Module_symvers_exact_501'] and compat['public_headers_unchanged']
    assert compat['archive_order_exact'] and not compat['diagnostics']
    assert a['new_build_receipt_sha256']==pins['receipts']['build-result.json']
    assert a['actual_502_comparisons']==compat
    assert e['returncode']==0 and e['same_original_exec_handle_waited'] and e['no_live_build_process_remaining']
    assert r['identity']['KBUILD_BUILD_VERSION']=='502' and r['identity']['UTS_RELEASE']=='7.3.0-rc6-rmx1931-samurai-k363+'
    assert r['private_output']=='/home/cy122/charging-management-20261023/gauge-image502-notify-01'
    im=build['outputs']['arch/arm64/boot/Image']
    assert im==delivery['outputs']['arch/arm64/boot/Image']
    assert im['sha256']==pins['Image_sha256'] and im['bytes']==pins['Image_bytes']
    assert pins['Image_sha256']!='3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'
    return pins

def check_local():
    old=pinned(OLD,'7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9')
    f=parse_fat(old)
    assert f['files']['Image']['sha256']=='3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'
    assert f['files']['Image']['size']==59243008
    assert f['files']['SAMURAI.DTB']['sha256']=='a82383fa30609bb5e1400f8af12055abdbca7373734c983549d9f437afae2cc5'
    for path,digest in TOOLS.values():pinned(Path(path),digest)
    proof=load_502_proof()
    if proof is None:
        return old,None,f
    image=pinned(IMAGE,proof['Image_sha256'])
    assert len(image)==proof['Image_bytes'] and len(image)>0
    return old,image,f
def execute():
    assert not OUT.exists(),'unique private directory exists; no replay'
    old,image,a=check_local()
    if image is None: raise RuntimeError('Image502 frozen terminal proof not supplied; no Image read or packaging')
    paths=[OLD,IMAGE,Path(__file__),HERE/'Image502-pins.json']+[HERE.parents[1]/'charging-ui-audit-20261023/gauge-image502-notify-candidate'/n for n in ['delivery.json','build-result.json','abi-reuse-result.json','execution-receipt.json']]+[Path(p) for p,_ in TOOLS.values()]
    before={str(p):sha(read_bytes(p)) for p in paths};mount=read_bytes(Path('/proc/self/mountinfo'))
    OUT.mkdir(parents=True);target=OUT/'logdump-gauge502-private.img'
    r={'passed':False,'scope':'private undeployed current-501 FAT Image502 replacement only','host_linux_pid':os.getpid(),
       'rollback_logdump_sha256':sha(old),'Image502_sha256':sha(image),'commands':[],'inputs_before':before}
    print(json.dumps({'started':True,'host_linux_pid':os.getpid(),'private_directory':str(OUT)}),flush=True)
    def run(name,args,stage):
        argv=[TOOLS[name][0]]+list(map(str,args));e={'stage':stage,'argv':argv};r['commands'].append(e);save(OUT/'result.json',r)
        with (OUT/(stage+'.stdout')).open('wb') as out,(OUT/(stage+'.stderr')).open('wb') as err:
            q=subprocess.run(argv,stdout=out,stderr=err,env=dict(os.environ,PATH='/usr/bin:/bin',MTOOLS_SKIP_CHECK='0'),timeout=120)
        e['returncode']=q.returncode;save(OUT/'result.json',r);assert q.returncode==0,stage+' failed'
    try:
        shutil.copyfile(OLD,target);assert read_bytes(target)==old
        run('mcopy',['-o','-i',target,IMAGE,'::/Image'],'replace-Image')
        run('mcopy',['-i',target,'::/Image',OUT/'Image-readback'],'readback-Image')
        assert read_bytes(OUT / 'Image-readback')==image
        new=read_bytes(target);b=parse_fat(new)
        assert b['files']['Image']['content']==image and b['files']['Image']['size']==len(image)
        assert b['files']['SAMURAI.DTB']==a['files']['SAMURAI.DTB'],'other FAT entry or contents changed'
        # Require all changed bytes to belong to Image data, its directory slots or
        # its old/new FAT16 chain entries. Preserve deleted slots and all slack elsewhere.
        ranges=[]
        for fs in [a,b]:
            im=fs['files']['Image'];ranges.extend((p,p+32) for p in im['entry_offsets'])
            for n in im['clusters']:
                p=fs['data_at']+(n-2)*fs['bps'];ranges.append((p,p+fs['bps']))
                for copy in range(2):
                    p=fs['fat_at']+copy*fs['fat_size']+n*2;ranges.append((p,p+2))
        merged=[]
        for lo,hi in sorted(ranges):
            if merged and lo<=merged[-1][1]:merged[-1]=(merged[-1][0],max(hi,merged[-1][1]))
            else:merged.append((lo,hi))
        pos=0
        for lo,hi in merged:assert old[pos:lo]==new[pos:lo],f'non-Image bytes changed before {lo}';pos=hi
        assert old[pos:]==new[pos:]
        run('fsck.fat',['-n',target],'fsck-readonly')
        assert read_bytes(target)==new,'fsck -n unexpectedly wrote'
        r.update(passed=True,logdump_path=str(target),logdump_bytes=len(new),logdump_sha256=sha(new),
                 only_Image_file_changed=True,other_entries_and_contents_exact=True,all_non_Image_bytes_exact=True,
                 Image_readback_exact=True,fsck_readonly_passed=True,native_DTB_untouched=True,
                 rootfs_R8_camera_untouched=True,no_device_or_deployment=True)
        save(OUT/'FAT-verification.json',{'old':{n:{k:v for k,v in f.items() if k not in ['content','entries','clusters']} for n,f in a['files'].items()},
             'new':{n:{k:v for k,v in f.items() if k not in ['content','entries','clusters']} for n,f in b['files'].items()},
             'permitted_Image_write_ranges':merged,'unchanged_outside_ranges':True})
    except BaseException as exc:r['error']=repr(exc);r['traceback']=traceback.format_exc()
    finally:
        r['inputs_after']={str(p):sha(read_bytes(p)) for p in paths};r['parent_inputs_unchanged']=before==r['inputs_after']
        r['parent_mountinfo_unchanged']=mount==read_bytes(Path('/proc/self/mountinfo'));r['passed'] &= r['parent_inputs_unchanged'] and r['parent_mountinfo_unchanged']
        r['artifacts']={p.name:sha(read_bytes(p)) for p in OUT.iterdir() if p.is_file() and p.name!='result.json'}
        save(OUT/'result.json',r)
        public={k:v for k,v in r.items() if k not in ['inputs_before','inputs_after','commands','artifacts','traceback']}
        public['private_result_sha256']=sha(read_bytes(OUT / 'result.json'));public['commands_sha256']=sha(json.dumps(r['commands'],sort_keys=True).encode())
        save(HERE/'logdump-result.json',public);print(json.dumps(public,indent=2))
    return 0 if r['passed'] else 1
if __name__=='__main__':
    if sys.argv[1:] in [[],['--check-local']]:
        _,image,_=check_local();print(json.dumps({'checked':True,'Image502_proof_ready':image is not None,'new_Image_read':image is not None,'tools_executed':False,'unique_private_exists':OUT.exists()}))
    elif sys.argv[1:]==['--execute-logdump']:raise SystemExit(execute())
    else:raise SystemExit('default --check-local; explicit --execute-logdump only')
