"""Reuse the reviewed debugfs listing parser for the newly extracted system."""
from pathlib import Path
import collections,hashlib,importlib.util,json,re
ROOT=Path('/mnt/e/RealmeX2Pro edk2')
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-oem-audit-20261023')
SOURCE=ROOT/'reference/charging-oem-audit-20261023/gauge-2719-vendor-name-index/index-vendor.py'
EXTRACT=PRIVATE/'gauge-2719-system-extract-private-01'
IMAGE=EXTRACT/'system.img';OUT=PRIVATE/'gauge-2719-system-name-index-private-01'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert not OUT.exists()
assert sha(SOURCE.read_bytes())=='d0db963cd49b2e96a37be21c87ece1a24908968e0d546531c70520e5d562138b'
spec=importlib.util.spec_from_file_location('reviewed_vendor_index',SOURCE)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
producer=json.loads((EXTRACT/'result-private.json').read_bytes())
assert producer['passed'] and producer['source_stat_unchanged'] and producer['tools_and_sources_unchanged']
assert producer['node_command']['terminal'] and producer['node_command']['returncode']==0
assert IMAGE.is_file() and not IMAGE.is_symlink() and IMAGE.stat().st_size==producer['image']['bytes']==4487905280
assert helper.sha_file(helper.DEBUGFS)==helper.DEBUGFS_SHA
with IMAGE.open('rb') as f:f.seek(1080);assert f.read(2)==b'\x53\xef'
before=IMAGE.stat();OUT.mkdir(mode=0o700)
report=dict(passed=False,scope='all reachable system names, no symlink traversal or content search',
 image_sha256=producer['image']['sha256'],image_bytes=before.st_size,
 image_SHA_reused_from_completed_producer=True,post_index_full_image_SHA_recomputed=False,
 producer_result_sha256=sha((EXTRACT/'result-private.json').read_bytes()),parser_sha256=sha(SOURCE.read_bytes()),
 debugfs_sha256=helper.DEBUGFS_SHA,mounted=False,device_SDK_or_Git_used=False)
commands=[]
try:
    queue=collections.deque([('/',2,0)]);seen=set();entries=[];paths=set()
    while queue:
        path,inode,depth=queue.popleft()
        helper.require(inode not in seen and depth<=64 and len(seen)<10000,'directory cycle or limit')
        seen.add(inode);rows=helper.list_directory(IMAGE,path,commands)
        for row in rows:
            helper.require(row['path'] not in paths,'duplicate full path');paths.add(row['path']);entries.append(row)
            helper.require(len(entries)<=100000,'entry limit')
            if row['kind']=='directory':queue.append((row['path'],row['inode'],depth+1))
        if len(seen)%128==0:print(json.dumps(dict(directories=len(seen),entries=len(entries),pending=len(queue))),flush=True)
    entries.sort(key=lambda row:row['path'])
    suffixes=('.bqz','.bqfs','.df.fs','.srec')
    descriptors=[r for r in entries if r['path'].lower().endswith(suffixes)]
    candidates=[r for r in entries if re.search(r'gauge|batt|charg|vooc|fastcg|bq2[78]|2719|engineer|factory',r['path'],re.I)]
    (OUT/'system-name-index.json').write_bytes(helper.encode(entries))
    (OUT/'candidate-names.json').write_bytes(helper.encode(dict(descriptor_suffix_matches=descriptors,candidate_names=candidates)))
    after=IMAGE.stat();assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
    report.update(passed=True,directories=len(seen),entries=len(entries),kinds=dict(collections.Counter(r['kind'] for r in entries)),
        descriptor_suffix_matches=descriptors,candidate_names=candidates,index_sha256=helper.sha_file(OUT/'system-name-index.json'),
        image_metadata_unchanged=True,actual_debugfs_children=len(commands),all_children_terminal0=all(c['terminal'] and c['returncode']==0 for c in commands),
        unused_inode_zero_slots=sum(c['unused_inode_zero_slots'] for c in commands),exact2719_model_or_protocol_established=False,
        embedded_or_compressed_contents_searched=False)
except BaseException as error:report.update(passed=False,error=repr(error));raise
finally:
    (OUT/'commands.json').write_bytes(helper.encode(commands));(OUT/'result-private.json').write_bytes(helper.encode(report))
print(json.dumps({key:report[key] for key in ['passed','directories','entries','kinds','actual_debugfs_children','index_sha256','candidate_names']}),flush=True)
