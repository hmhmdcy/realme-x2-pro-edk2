"""Read an extracted private vendor image with debugfs; never mount or deploy."""
from pathlib import Path,PurePosixPath
import argparse,collections,hashlib,json,os,re,stat,subprocess,sys
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-oem-audit-20261023')
DEBUGFS=Path('/usr/sbin/debugfs')
DEBUGFS_SHA='864e1d7b445e7b5bfc831da78330dbcafc590fa82b89ea9de60b7527f989954f'
def sha_file(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return (json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()
def require(ok,message):
    if not ok:raise ValueError(message)
def quote(path):
    require(not any(ord(c)<32 or ord(c)==127 for c in path),'control character in directory name')
    return '"'+path.replace('\\','\\\\').replace('"','\\"')+'"'
def list_directory(image,path,commands):
    argv=[str(DEBUGFS),'-R','ls -p '+quote(path),str(image)]
    child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:stdout,stderr=child.communicate()
    finally:child.wait()
    commands.append(dict(directory=path,pid=child.pid,terminal=True,returncode=child.returncode,
                         stdout_sha256=sha(stdout),stderr_sha256=sha(stderr)))
    require(child.returncode==0,'debugfs child failed')
    diagnostic=stderr.decode('utf-8').splitlines()
    require(diagnostic and diagnostic[0].startswith('debugfs 1.47.2 '),'unexpected debugfs identity')
    require(not any(line.strip() for line in diagnostic[1:]),'debugfs reported an error')
    rows=[];unused_slots=0
    for line in stdout.decode('utf-8').splitlines():
        if not line.strip():continue
        fields=line.split('/')
        require(len(fields)==8 and fields[0]==fields[-1]=='','unrecognized debugfs listing: '+repr(line[:160]))
        _,inode,mode,uid,gid,name,size,_=fields
        require(inode.isdecimal() and re.fullmatch('[0-7]+',mode) and uid.isdecimal() and gid.isdecimal(),'invalid inode metadata')
        if int(inode)==0:
            require(int(mode,8)==0 and uid==gid=='0' and size=='0','unexpected unused inode metadata')
            unused_slots+=1;continue
        require(name and '/' not in name and '\x00' not in name,'invalid name')
        if name in ['.','..']:continue
        require(not size or size.isdecimal(),'invalid size')
        value=int(mode,8);kind='directory' if stat.S_ISDIR(value) else 'symlink' if stat.S_ISLNK(value) else 'regular' if stat.S_ISREG(value) else 'other'
        rows.append(dict(path=(PurePosixPath(path)/name).as_posix(),inode=int(inode),mode=mode,
                         uid=int(uid),gid=int(gid),bytes=int(size) if size else None,kind=kind))
    require(len({r['path'] for r in rows})==len(rows),'duplicate directory entry')
    commands[-1]['unused_inode_zero_slots']=unused_slots
    return rows
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',type=Path,required=True);parser.add_argument('--image-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    image=args.image.resolve();out=args.output.resolve();root=PRIVATE.resolve()
    require(args.image.is_file() and not args.image.is_symlink() and image.is_relative_to(root),'private ordinary image required')
    require(out.is_relative_to(root) and out!=root and not out.exists(),'unique private output required')
    require(image.stat().st_size==1711276032 and re.fullmatch('[0-9a-f]{64}',args.image_sha256),'fixed F10 extent/hash required')
    require(sha_file(image)==args.image_sha256,'image content differs')
    require(sha_file(DEBUGFS)==DEBUGFS_SHA,'debugfs binary differs')
    with image.open('rb') as f:f.seek(1080);require(f.read(2)==b'\x53\xef','EXT filesystem magic missing')
    before=image.stat();out.mkdir(mode=0o700)
    report=dict(passed=False,scope='all reachable vendor names, without symlink traversal or content search',
        image_sha256=args.image_sha256,image_bytes=before.st_size,debugfs_sha256=DEBUGFS_SHA,
        mounted=False,device_SDK_storage_or_Git_used=False)
    commands=[]
    try:
        queue=collections.deque([('/',2,0)]);seen=set();entries=[];paths=set()
        while queue:
            path,inode,depth=queue.popleft()
            require(inode not in seen and depth<=64 and len(seen)<10000,'directory cycle or limit')
            seen.add(inode);rows=list_directory(image,path,commands)
            for row in rows:
                require(row['path'] not in paths,'duplicate full path');paths.add(row['path']);entries.append(row)
                require(len(entries)<=100000,'entry limit exceeded')
                if row['kind']=='directory':queue.append((row['path'],row['inode'],depth+1))
            if len(seen)%32==0:print(json.dumps(dict(directories=len(seen),entries=len(entries),pending=len(queue))),flush=True)
        entries.sort(key=lambda row:row['path'])
        suffixes=('.bqz','.bqfs','.df.fs','.srec')
        descriptors=[r for r in entries if r['path'].lower().endswith(suffixes)]
        candidates=[r for r in entries if re.search(r'gauge|batt|charg|vooc|fastcg|bq2[78]|2719',r['path'],re.I)]
        (out/'vendor-name-index.json').write_bytes(encode(entries))
        (out/'candidate-names.json').write_bytes(encode(dict(descriptor_suffix_matches=descriptors,candidate_names=candidates)))
        after=image.stat();require((before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),'image changed during listing')
        report.update(passed=True,all_reachable_names_enumerated=True,directories=len(seen),entries=len(entries),
            kinds=dict(collections.Counter(r['kind'] for r in entries)),descriptor_suffix_matches=descriptors,
            candidate_names=candidates,index_sha256=sha_file(out/'vendor-name-index.json'),
            image_metadata_unchanged=True,actual_debugfs_children=len(commands),all_children_terminal0=all(c['terminal'] and c['returncode']==0 for c in commands),
            unused_inode_zero_slots=sum(c['unused_inode_zero_slots'] for c in commands),
            exact2719_model_or_protocol_established=False,embedded_or_compressed_contents_searched=False)
    except BaseException as error:report.update(passed=False,error=repr(error));raise
    finally:
        (out/'commands.json').write_bytes(encode(commands));(out/'result.json').write_bytes(encode(report))
    print(json.dumps({key:report[key] for key in ['passed','directories','entries','kinds','actual_debugfs_children','index_sha256']}))
if __name__=='__main__':main()
