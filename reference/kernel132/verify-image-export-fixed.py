from pathlib import Path
import runpy,os,stat,hashlib,json
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel129/ensure-rootfs-volume.py')
stage=Path('/home/cy122/pmos-samurai-rootfs129');root=stage/'rootfs132';export=stage/'image-export132-fixed';out=Path('/mnt/e/edk2-samurai-out/kernel132');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel132')
assert export.is_dir()
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()
def manifest(folder):
    result={}
    for parent,dirs,files in os.walk(folder,followlinks=False):
        for name in dirs+files:
            p=Path(parent)/name;relative=p.relative_to(folder).as_posix();s=p.lstat()
            item=dict(mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
            if stat.S_ISREG(s.st_mode):item.update(size=s.st_size,sha256=sha(p))
            elif stat.S_ISLNK(s.st_mode):item['target']=os.readlink(p)
            elif stat.S_ISCHR(s.st_mode) or stat.S_ISBLK(s.st_mode):item['rdev']=s.st_rdev
            item['xattrs']={key:hashlib.sha256(os.getxattr(p,key,follow_symlinks=False)).hexdigest() for key in os.listxattr(p,follow_symlinks=False)}
            result[relative]=item
    return result
expected=manifest(root);actual=manifest(export)
differences=[]
for name in sorted(expected.keys()|actual.keys()):
    if expected.get(name)!=actual.get(name):differences.append(dict(path=name,expected=expected.get(name),actual=actual.get(name)))
(out/'image-export-fixed-differences-private.json').write_text(json.dumps(differences,indent=2)+'\n')
(out/'image-export-fixed-manifest-private.json').write_text(json.dumps(actual,sort_keys=True)+'\n')
report=dict(expected_entries=len(expected),export_entries=len(actual),differing_entries=len(differences),all_content_and_mode_uid_gid_symlinks_xattrs_match=not differences,no_phone_changes=True)
(ref/'image-export-fixed-content-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert not differences
