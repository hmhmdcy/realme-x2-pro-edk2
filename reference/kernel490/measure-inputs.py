"""Measure and hash only the seven cached roots selected for490; no mutation."""
from pathlib import Path
import hashlib,json,shutil
import storage
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel490')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def inventory(root):
    result={}
    for path in sorted(root.rglob('*')):
        name=path.relative_to(root).as_posix()
        if path.is_symlink():result[name]={'symlink':path.readlink().as_posix()}
        elif path.is_file():result[name]=dict(sha256=sha(path),bytes=path.stat().st_size,mode=path.stat().st_mode&0o7777)
    return result

def main():
    work=storage.workspace();PRIVATE.mkdir(exist_ok=True)
    old=PRIVATE.parent/'kernel475';state=json.loads((old/'package-state-r1-private.json').read_text())
    by_name={row['name']:row['after_files'] for row in state['inventories']};rows=[];total=0
    for name,root in state['roots'].items():
        actual=inventory(Path(root));assert actual==by_name[name],name
        size=sum(row.get('bytes',0) for row in actual.values());total+=size
        rows.append(dict(name=name,files=len(actual),regular_bytes=size))
    free=shutil.disk_usage(work.parent).free
    # Both a copy and verification extraction can coexist, with the required reserve.
    assert free>2*1024**3+2*total+128*1024**2
    report=dict(stage=490,passed=True,cached_roots=rows,cached_root_file_entries=sum(row['files'] for row in rows),
        total_regular_bytes=total,free_before_bytes=free,required_reserve_bytes=2*1024**3,no_sdk=True,no_device=True,
        cached_package_state_sha256=sha(old/'package-state-r1-private.json'))
    (PRIVATE/'input-measurement-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
