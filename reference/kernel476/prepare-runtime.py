"""Materialise an unbound offline template, or bind a fresh476 handoff locally.

No transport, SDK binding, build, or target-client execution entry point.
"""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,re,shutil,struct,sys,tarfile
from datetime import datetime,timezone
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out');PRIVATE=P/'kernel476'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff',type=Path)
    parser.add_argument('--window-id',default='k476-control-delay-r1')
    args=parser.parse_args();assert re.fullmatch(r'k476-control-delay-r([1-9]|1[0-9]|20)',args.window_id)
    spec=importlib.util.spec_from_file_location('guard476',HERE.parent/'kernel284/storage.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.mounted_build()
    PRIVATE.mkdir(exist_ok=True)
    # Read retained363 originals; never use local or target uname as expected.
    image=P/'kernel363/Image-k363-private';assert sha(image)=='15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'
    release=json.loads((P/'kernel363/postboot-adoption-private.json').read_text())['release']
    banners=re.findall(rb'Linux version '+re.escape(release.encode())+rb'[^\x00\n]{20,500}',image.read_bytes())
    assert banners and len(set(banners))==1
    version=banners[0].decode().split(') #363 ',1)[1];version='#363 '+version
    expected=dict(release=release,version=version,image_sha256=sha(image),
        adoption_sha256=sha(P/'kernel363/postboot-adoption-private.json'))
    (PRIVATE/'expected-uname-private.json').write_text(json.dumps(expected,indent=2)+'\n')
    work=PRIVATE/(args.window_id+('-bound' if args.handoff else '-offline-template'))
    assert not work.exists(),'Never overwrite a prepared transaction'
    work.mkdir(mode=0o700)
    old=P/'kernel473/prepared-r1';mapping=json.loads((old/'payload-files-private.json').read_text())
    oldplan=json.loads((old/'tele-plan-private.json').read_text())
    files={name:Path(path) for name,path in mapping.items() if name.startswith(('lib/','ipa/','proxy/'))}
    assert sha(files['lib/libcamera.so.0.7.2'])=='9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af'
    assert sha(files['proxy/camss_ipa_proxy'])=='c7887708377b92b167d917173cb2840a78e437a773985fa087ef980bd382038c'
    assert all(sha(path)==oldplan['common_payload'][name] for name,path in files.items())
    tools=json.loads((HERE.parent/'kernel472/tools-build-validation.json').read_text());assert tools['passed']
    for row in tools['tools']:
        path=Path(row['path']);assert sha(path)==row['sha256'];files[path.name]=path
    profile=PRIVATE/'mode2-measurement-private.yaml'
    wanted='''version: 2
sensor_model: s5k3m5
modes:
- match:
    width: 4208
    height: 2368
    pixel_rate: 481930000
    line_length: 4848
    frame_length: 3312
  residual_black_subtraction: 3840
  range_normalization: 1.06201171875
'''
    if profile.exists():assert profile.read_text()==wanted
    else:profile.write_text(wanted)
    assert not any(key in wanted for key in ['sensor_controls','exposure_delay','gain_delay','agc:','awb:','ipe:'])
    files['mode2-measurement-private.yaml']=profile
    common_payload={name:sha(path) for name,path in files.items()}
    for name in ['pipeline-fixture','user-launcher.py']:files[name]=Path(mapping[name])
    assert sha(files['pipeline-fixture'])=='bad0dc79d95d070f089c158b159a21f72a44a459f4c1606f9c27493457863a43'
    # Exact successful473 worker retains the reviewed unload/load/restore order.
    assert sha(old/'worker.py')=='ffd770cafbf1a654ae97fc838289f096c032fd3b4c1706f3cef2d61288092653'
    worker=(old/'worker.py').read_text().replace("'stage':473","'stage':476")
    marker="marker=root/'state.json'"
    early='''# Reject unbound/stale preparations before any target inventory or mutation.
plan=json.loads((root/'tele-plan-private.json').read_text())
assert plan['deployable'] and root.name==plan['window_id']
handoff=json.loads((root/'handoff-private.json').read_text())
assert handoff['fresh_preflight_verified'] and handoff['window_id']==root.name
from datetime import datetime,timezone
stamp=datetime.fromisoformat(handoff['issued_at_utc'].replace('Z','+00:00'))
assert 0<=(datetime.now(timezone.utc)-stamp).total_seconds()<=600
assert os.uname().release==plan['expected_uname']['release'] and os.uname().version==plan['expected_uname']['version']
'''
    assert worker.count(marker)==1;worker=worker.replace(marker,early+marker);ast.parse(worker)
    (work/'worker.py').write_text(worker);files['worker.py']=work/'worker.py'
    helper=old/'capture-common-private.py'
    assert sha(helper)=='f2a90ceddc686cac69415d54991228847881c007cfa11606aece0327ee325b33'
    helpertext=helper.read_text().replace('k473-ipe-capacity-','k476-control-delay-')
    ast.parse(helpertext);(work/'capture-common-private.py').write_text(helpertext);files['capture-common-private.py']=work/'capture-common-private.py'
    files['capture-body-tele.py']=HERE/'capture-body-control.py'
    modules=json.loads((HERE.parent/'kernel441/intree-build-validation.json').read_text());assert modules['passed']
    proof={}
    for row in modules['modules']:
        if not row['runtime_candidate']:continue
        path=Path(row['private_path']);assert sha(path)==row['sha256'];name=row['name'].replace('-','_')
        files[row['name']+'.ko']=path
        proof[name]=dict(file=row['name']+'.ko',sha256=sha(path),note_sha256=json.loads((old/'proof.json').read_text())['modules'][name]['note_sha256'])
    sensor=P/'kernel468/s5k3m5-mode2-build2.ko';sensorproof=json.loads((HERE.parent/'kernel468/module-build-validation.json').read_text())
    assert sensorproof['passed'] and sha(sensor)==sensorproof['module_sha256']
    files['s5k3m5-mode2.ko']=sensor
    proof=dict(modules=proof,sensor=dict(json.loads((old/'proof.json').read_text())['sensor']))
    assert proof['sensor']['sha256']==sha(sensor)
    handoff=None
    if args.handoff:
        handoff=json.loads(args.handoff.read_text())
        assert handoff['fresh_preflight_verified'] and handoff['window_id']==args.window_id and handoff['window_owner']=='camera'
        stamp=datetime.fromisoformat(handoff['issued_at_utc'].replace('Z','+00:00'))
        assert 0<=(datetime.now(timezone.utc)-stamp).total_seconds()<=600
        assert handoff['expected_uname']==expected
        baseline=args.handoff.parent/'baseline-private.json';assert sha(baseline)==handoff['formal_baseline_sha256']
        assert 'tele_sensor' in json.loads(baseline.read_text())
        files['handoff-private.json']=args.handoff;files['baseline-private.json']=baseline
        proof['boot_guard']=handoff['boot_guard_path']
    else:proof['boot_guard']='FRESH_K476_HANDOFF_REQUIRED'
    (work/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');files['proof.json']=work/'proof.json'
    plan=dict(stage=476,kind='sensor-control-delay',window_id=args.window_id,deployable=handoff is not None,
        kernel_release=release,expected_uname=expected,common_payload=common_payload,
        actual_sensor=[4208,2368],expected_ll=4848,expected_fll=3312,linear_bhist_roi=[0,0,4208,2368],
        no_ae=True,no_delayed_controls=True,delay_not_preset=True)
    (work/'tele-plan-private.json').write_text(json.dumps(plan,indent=2)+'\n');files['tele-plan-private.json']=work/'tele-plan-private.json'
    for name,path in files.items():
        if name.endswith('.py'):ast.parse(path.read_text())
    manifest={name:sha(path) for name,path in files.items()}
    (work/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');files['manifest.json']=work/'manifest.json'
    (work/'payload-files-private.json').write_text(json.dumps({name:str(path) for name,path in files.items()},indent=2)+'\n')
    archive=work/'control-delay-payload.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for name,path in files.items():tar.add(path,arcname=name,recursive=False)
    report=dict(stage=476,prepared=True,deployable=handoff is not None,files=len(files),archive_sha256=sha(archive),
        old461_core_and_proxy=True,controlled473_worker_order_reused=True,mode2_sensor468=True,
        tools472_reused=True,profile_sha256=sha(profile),expected_uname_from_frozen363_image=True,
        no_sdk=True,no_build=True,no_upload=True,no_client_execution=True,mode2_delay_measured=False,passed=True)
    # Keep the issued public offline-template receipt frozen. Future bindings
    # receive their own private receipt instead of rewriting deployable=false.
    (work/'preparation-private.json').write_text(json.dumps(report,indent=2)+'\n')
    (PRIVATE/'prepared-last-private.json').write_text(json.dumps(dict(work=str(work),**report),indent=2)+'\n')
    print(json.dumps(dict(work=str(work),**report)))

if __name__=='__main__':main()
