"""Only privately replace ACA FAT /Image. Default is read-only; never deploys."""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=Path('/mnt/e/edk2-samurai-out')
OLD=ROOT/'kernel365/logdump-k365-candidate-private.img'
IMAGE=Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01/build/arch/arm64/boot/Image')
OUT=ROOT/'charging-management-20261023/gauge-image501-logdump-private-01'
sha=lambda b:hashlib.sha256(b).hexdigest()
TOOLS={'mcopy':('/usr/bin/mcopy','ff7249e732c43e4f00716fdd1f50515e012d51c38f536d18e1e25bf57f372f8c'),
       'fsck.fat':('/usr/sbin/fsck.fat','4e2aa9699ac6a103b8d27e1c0bceb8f8e6a817ff067f97cb240918e5aa75ae5c')}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def pinned(p,d):
    b=p.read_bytes();assert sha(b)==d,str(p)+' differs';return b
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
def check_local():
    old=pinned(OLD,'aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da')
    image=pinned(IMAGE,'3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02')
    f=parse_fat(old)
    assert f['files']['Image']['sha256']=='15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'
    assert f['files']['Image']['size']==len(image)==59243008
    assert f['files']['SAMURAI.DTB']['sha256']=='a82383fa30609bb5e1400f8af12055abdbca7373734c983549d9f437afae2cc5'
    for path,digest in TOOLS.values():pinned(Path(path),digest)
    return old,image,f
def execute():
    assert not OUT.exists(),'unique private directory exists; no replay'
    old,image,a=check_local();paths=[OLD,IMAGE,Path(__file__)]+[Path(p) for p,_ in TOOLS.values()]
    before={str(p):sha(p.read_bytes()) for p in paths};mount=Path('/proc/self/mountinfo').read_bytes()
    OUT.mkdir(parents=True);target=OUT/'logdump-gauge501-private.img'
    r={'passed':False,'scope':'private undeployed ACA FAT Image501 replacement only','host_linux_pid':os.getpid(),
       'rollback_logdump_sha256':sha(old),'Image501_sha256':sha(image),'commands':[],'inputs_before':before}
    print(json.dumps({'started':True,'host_linux_pid':os.getpid(),'private_directory':str(OUT)}),flush=True)
    def run(name,args,stage):
        argv=[TOOLS[name][0]]+list(map(str,args));e={'stage':stage,'argv':argv};r['commands'].append(e);save(OUT/'result.json',r)
        with (OUT/(stage+'.stdout')).open('wb') as out,(OUT/(stage+'.stderr')).open('wb') as err:
            q=subprocess.run(argv,stdout=out,stderr=err,env=dict(os.environ,PATH='/usr/bin:/bin',MTOOLS_SKIP_CHECK='0'),timeout=120)
        e['returncode']=q.returncode;save(OUT/'result.json',r);assert q.returncode==0,stage+' failed'
    try:
        shutil.copyfile(OLD,target);assert target.read_bytes()==old
        run('mcopy',['-o','-i',target,IMAGE,'::/Image'],'replace-Image')
        run('mcopy',['-i',target,'::/Image',OUT/'Image-readback'],'readback-Image')
        assert (OUT/'Image-readback').read_bytes()==image
        new=target.read_bytes();b=parse_fat(new)
        assert b['files']['Image']['content']==image and b['files']['Image']['size']==a['files']['Image']['size']
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
        assert target.read_bytes()==new,'fsck -n unexpectedly wrote'
        r.update(passed=True,logdump_path=str(target),logdump_bytes=len(new),logdump_sha256=sha(new),
                 only_Image_file_changed=True,other_entries_and_contents_exact=True,all_non_Image_bytes_exact=True,
                 Image_readback_exact=True,fsck_readonly_passed=True,native_DTB_untouched=True,
                 rootfs_R8_camera_untouched=True,no_device_or_deployment=True)
        save(OUT/'FAT-verification.json',{'old':{n:{k:v for k,v in f.items() if k not in ['content','entries','clusters']} for n,f in a['files'].items()},
             'new':{n:{k:v for k,v in f.items() if k not in ['content','entries','clusters']} for n,f in b['files'].items()},
             'permitted_Image_write_ranges':merged,'unchanged_outside_ranges':True})
    except BaseException as exc:r['error']=repr(exc);r['traceback']=traceback.format_exc()
    finally:
        r['inputs_after']={str(p):sha(p.read_bytes()) for p in paths};r['parent_inputs_unchanged']=before==r['inputs_after']
        r['parent_mountinfo_unchanged']=mount==Path('/proc/self/mountinfo').read_bytes();r['passed'] &= r['parent_inputs_unchanged'] and r['parent_mountinfo_unchanged']
        r['artifacts']={p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.is_file() and p.name!='result.json'}
        save(OUT/'result.json',r)
        public={k:v for k,v in r.items() if k not in ['inputs_before','inputs_after','commands','artifacts','traceback']}
        public['private_result_sha256']=sha((OUT/'result.json').read_bytes());public['commands_sha256']=sha(json.dumps(r['commands'],sort_keys=True).encode())
        save(HERE/'logdump-result.json',public);print(json.dumps(public,indent=2))
    return 0 if r['passed'] else 1
if __name__=='__main__':
    if sys.argv[1:] in [[],['--check-local']]:
        check_local();print(json.dumps({'checked':True,'tools_executed':False,'unique_private_exists':OUT.exists()}))
    elif sys.argv[1:]==['--execute-logdump']:raise SystemExit(execute())
    else:raise SystemExit('default --check-local; explicit --execute-logdump only')
