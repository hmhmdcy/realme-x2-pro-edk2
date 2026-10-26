"""Exercise recovery boundaries on temporary files, never a device or partition."""
from pathlib import Path
import hashlib,importlib.util,json,os,tempfile
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('image505_guard_test',HERE/'boot-guard.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
cases=[]
with tempfile.TemporaryDirectory(prefix='samurai-image505-guard-') as folder:
    g.ROOT=Path(folder);path=g.ROOT/'atomic'
    g.atomic(path,b'old',0o600);g.atomic(path,b'new',0o640)
    assert path.read_bytes()==b'new' and path.stat().st_mode&0o777==0o640 and not path.with_name(path.name+'.image505-next').exists()
    cases.append('atomic replacement data, mode and temporary cleanup')
    link=g.ROOT/'link';link.symlink_to(path)
    try:g.regular(link)
    except AssertionError:pass
    else:raise AssertionError('symlink accepted')
    cases.append('symlink is rejected before recovery reads')
    token='test-boot-bound-token';manifest='a'*64
    meta={'token':token,'files':{'/usr/share/samurai-charging/manifest.json':{'new':{'sha256':manifest}}}}
    expected=dict(boot=g.boot(),token=token,manifest=manifest)
    g.atomic(g.ROOT/'accepted.json',(json.dumps(expected)+'\n').encode());assert g.acknowledged(meta)
    expected['boot']='another-boot';g.atomic(g.ROOT/'accepted.json',json.dumps(expected).encode());assert not g.acknowledged(meta)
    cases.append('a prior boot acknowledgment cannot suppress this trial timeout')
    actions=[];g.write_part=lambda meta,name,side:actions.append((name,side));g.restore_files=lambda meta:actions.append('rootfs')
    g.os.sync=lambda:None
    g.rollback(meta,'test',False)
    assert actions==[('boot','old'),('logdump','old'),'rootfs']
    assert json.loads((g.ROOT/'state.json').read_bytes())['event']=='restored'
    cases.append('rollback orders old firmware before old kernel and restores rootfs')
    actions.clear();g.prestart(meta)
    assert actions==[('boot','old'),('logdump','old'),'rootfs']
    cases.append('unexpected kernel restores the prior cohort before managed charging starts')
report=dict(passed=True,cases=cases,source_sha256=hashlib.sha256((HERE/'boot-guard.py').read_bytes()).hexdigest(),phone_accessed=False,partition_accessed=False)
(HERE/'boot-guard-test-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
