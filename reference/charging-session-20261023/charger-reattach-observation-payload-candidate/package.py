"""Offline two-file payload and exact IRQ-baseline rollback; no installer/transport."""
from pathlib import Path
import argparse,copy,gzip,hashlib,importlib.util,io,json,os,tarfile

HERE=Path(__file__).resolve().parent; REF=HERE.parents[1]
PRIVATE=Path('E:/edk2-samurai-out/charging-management-20261023')
OUT=PRIVATE/'charger-reattach-observation-payload-private-01'
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
KO='/lib/modules/'+RELEASE+'/extra/samurai-charging/samurai-mp2650.ko'
MANIFEST='/usr/share/samurai-charging/manifest.json'
OLD='10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f'
NEW='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'
BASE_MANIFEST='5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
NEW_NOTE='fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'
OLD_NOTE='f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'
MODULE=REF/'charging-session-20261023/charger-reattach-observation-module-candidate'
COHORT=REF/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def need(ok,message):
    if not ok:raise ValueError(message)

def local(path):
    value=str(path).replace('\\','/')
    if os.name=='nt' and value.startswith('/mnt/e/'):value='E:/'+value[7:]
    if os.name!='nt' and value.startswith('E:/'):value='/mnt/e/'+value[3:]
    return Path(value)

def checked(path,digest):
    path=local(path);need(path.is_file() and not path.is_symlink() and path.stat().st_size<2_000_000,'bounded ordinary input')
    raw=path.read_bytes();need(sha(raw)==digest,'input digest: '+str(path));return raw

def method():
    checked(COHORT/'cohort.py','421edb515a280fc575e3c37b6b5da1643179ac30b739469b57d8ad9fe8c4e7c7')
    spec=importlib.util.spec_from_file_location('exact_existing_cohort_module_identity',COHORT/'cohort.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def new_manifest(raw):
    need(sha(raw)==BASE_MANIFEST and raw.count(OLD.encode())==2,'exact current IRQ manifest bytes')
    old=json.loads(raw)
    need(old['modules']['samurai-mp2650']=={'target':KO,'sha256':OLD} and old['installed_files'][KO]==OLD,'charger base entries')
    expected=copy.deepcopy(old);expected['modules']['samurai-mp2650']['sha256']=NEW;expected['installed_files'][KO]=NEW
    result=raw.replace(OLD.encode(),NEW.encode())
    need(json.loads(result)==expected and result.replace(NEW.encode(),OLD.encode())==raw,'only two charger hash byte spans may change')
    return result

def check_archive(raw,files):
    need(set(files)=={KO,MANIFEST},'exact two replacement targets')
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        members=archive.getmembers();need(len(members)==2 and len({m.name for m in members})==2 and
            {m.name for m in members}=={name.lstrip('/') for name in files},'exact archive members')
        for member in members:
            need(member.isfile() and member.uid==member.gid==0 and member.uname==member.gname=='root' and
                 member.mode==0o600 and member.mtime==0 and not member.pax_headers,'archive metadata')
            content=archive.extractfile(member).read()
            need(member.size==len(files['/'+member.name]) and content==files['/'+member.name],'archive member bytes')

def archive(files):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for name,raw in sorted(files.items()):
            entry=tarfile.TarInfo(name.lstrip('/'));entry.uid=entry.gid=0;entry.uname=entry.gname='root'
            entry.mode=0o600;entry.mtime=0;entry.size=len(raw);tar.addfile(entry,io.BytesIO(raw))
    packed=io.BytesIO()
    with gzip.GzipFile(filename='',mode='wb',fileobj=packed,mtime=0) as sink:sink.write(stream.getvalue())
    raw=packed.getvalue();check_archive(raw,files);return raw

def inputs():
    paths={}; data={}
    def read(name,path,digest):
        paths[name]=local(path);data[name]=checked(path,digest);return data[name]
    delivery=json.loads(read('module_delivery',MODULE/'delivery.json','bca6889d077589741f5fde626555d95f7b7afe2720effd02247d01fb08e45b87'))
    receipt=json.loads(read('module_receipt',MODULE/'ko-result.json',delivery['files']['ko-result.json']['sha256']))
    need(delivery['passed'] is True and receipt['passed'] is True and receipt['module_sha256']==delivery['module_sha256']==NEW and
         receipt['module_bytes']==156800 and receipt['module_note_sha256']==NEW_NOTE,'actual new module receipt')
    need(receipt['intree'] is True and receipt['config_and_autoconf_exact_Image502'] is True and
         receipt['all_imports_from_Image502_builtin'] is True and receipt['diagnostics']==[] and
         receipt['commands'] and all(c['terminal'] is True and c['returncode']==0 for c in receipt['commands']),'Image502 compile/import/terminal evidence')
    current=json.loads(read('cohort_delivery',COHORT/'delivery.json','3d5b78bc4c7a6b476bfb97c2fbad3e0d76497c94e13bd755a8e4aaa0b032a07b'))
    need(current['passed'] is True and current['frozen'] is True,'frozen IRQ cohort')
    baseline=read('baseline_manifest',COHORT/'manifest.json',BASE_MANIFEST)
    protocol=json.loads(read('cohort_protocol',COHORT/'cohort-manifest.json',current['files']['cohort-manifest.json']['sha256']))
    tools=method();carriers={**protocol['required_carriers'],'Image502_sha256':protocol['Image502_sha256']};tools.validate_carriers(carriers)
    old=read('old_charger',PRIVATE/'r8-candidate/samurai-mp2650.ko',OLD)
    new=read('new_charger',receipt['private_module_path'],NEW)
    old_id,new_id=tools.module_identity(old,'samurai-mp2650'),tools.module_identity(new,'samurai-mp2650')
    need(old_id['resident_note_sha256']==OLD_NOTE and new_id['resident_note_sha256']==NEW_NOTE and
         len(old)==155512 and len(new)==156800,'actual ELF/name/intree/vermagic/note binding')
    r8=read('old_R8_archive',PRIVATE/'r8-candidate/thermal-bands-payload.tar.gz','f2bcbe500463114a407d93ddb4e2081db179f61dcc35d0a194abb4d18b2a5722')
    with tarfile.open(fileobj=io.BytesIO(r8),mode='r:gz') as tar:
        need(len(tar.getmembers())==2 and tar.extractfile(KO.lstrip('/')).read()==old,'rollback charger equals original R8 payload')
    meta=json.loads(baseline)
    need(meta['modules']['samurai-usb-input']['sha256']=='7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f' and
         meta['modules']['samurai-gauge-protection']['sha256']=='7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044','current retained provider module hashes')
    forward={KO:new,MANIFEST:new_manifest(baseline)};rollback={KO:old,MANIFEST:baseline}
    details={'input_files':{name:{'path':str(paths[name]),'sha256':sha(raw),'bytes':len(raw)} for name,raw in data.items()},
        'new_charger':new_id,'old_charger':old_id,'retained_carriers':carriers,
        'retained_provider_notes':{name:protocol['modules'][name]['new']['resident_note_sha256'] for name in
             ('samurai-usb-input','samurai-gauge-protection')},'actual_runtime_ABI_or_live_identity_verified':False}
    return details,forward,rollback

def materialize(out,details,forward,rollback):
    need(not Path(out).exists(),'new private output already exists; no overwrite')
    packed=archive(forward);back=archive(rollback)
    out=Path(out);out.mkdir(mode=0o700)
    for name,raw in [('forward-two-files.tar.gz',packed),('rollback-10ec-5fca-two-files.tar.gz',back),
                     ('manifest-new.json',forward[MANIFEST]),('manifest-rollback.json',rollback[MANIFEST])]:
        with (out/name).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    check_archive((out/'forward-two-files.tar.gz').read_bytes(),forward)
    check_archive((out/'rollback-10ec-5fca-two-files.tar.gz').read_bytes(),rollback)
    need((out/'manifest-new.json').read_bytes()==forward[MANIFEST] and (out/'manifest-rollback.json').read_bytes()==rollback[MANIFEST],'manifest disk readback')
    for row in details['input_files'].values():need(sha(local(row['path']).read_bytes())==row['sha256'],'original input changed')
    result={'schema':'samurai-charger-reattach-offline-two-file-payload-v1','passed':True,'private_output':str(out),
        'forward':{'path':str(out/'forward-two-files.tar.gz'),'sha256':sha(packed),'bytes':len(packed)},
        'rollback':{'path':str(out/'rollback-10ec-5fca-two-files.tar.gz'),'sha256':sha(back),'bytes':len(back)},
        'old_manifest_sha256':BASE_MANIFEST,'new_manifest_sha256':sha(forward[MANIFEST]),
        'forward_files':{name:sha(raw) for name,raw in forward.items()},'rollback_files':{name:sha(raw) for name,raw in rollback.items()},
        'all_other_manifest_bytes_and_entries_unchanged':True,**details,'original_inputs_unchanged':True,
        'deployment_transaction_guard_or_lease_created':False,'installed_or_device_accessed':False,
        'USB_protection_reloaded_or_MAC_attempt_reset':False,'r8_updater_directly_usable':False}
    (HERE/'payload-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--materialize',action='store_true');args=p.parse_args()
    details,forward,rollback=inputs()
    if not args.materialize:
        print(json.dumps({'source_and_cached_inputs_checked':True,'runtime_identity_or_request_created':False,'device_accessed':False}));return
    result=materialize(local(OUT),details,forward,rollback)
    print(json.dumps({'passed':True,'forward':result['forward'],'rollback':result['rollback'],'new_manifest_sha256':result['new_manifest_sha256']}))

if __name__=='__main__':main()
