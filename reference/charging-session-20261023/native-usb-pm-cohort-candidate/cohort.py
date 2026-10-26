"""Offline two-file native-USB PM cohort. No device access or installation."""
from pathlib import Path
import argparse,copy,gzip,hashlib,importlib.util,io,json,os,sys,tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PRIVATE=Path('E:/edk2-samurai-out/charging-management-20261023')
OUT=PRIVATE/'native-usb-pm-budget504-cohort-private-01'
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
USB='samurai-usb-input'
MANIFEST='/usr/share/samurai-charging/manifest.json'
REVISION='usb-native-pm-order-01'
METHOD=HERE.parent.parent/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate/cohort.py'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)
need(sha(METHOD.read_bytes())=='421edb515a280fc575e3c37b6b5da1643179ac30b739469b57d8ad9fe8c4e7c7','frozen helper method')
spec=importlib.util.spec_from_file_location('_original_pure_identity_helpers',METHOD)
method=importlib.util.module_from_spec(spec);spec.loader.exec_module(method)
module_identity=method.module_identity
def encode(value):return (json.dumps(value,indent=2)+'\n').encode()
def file_sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def pinned(entry):
    p=Path(entry['path']);need(p.is_file() and not p.is_symlink(),'input file')
    need(file_sha(p)==entry['sha256'] and p.stat().st_size==entry['bytes'],'input identity: '+str(p))
    return p
def make_manifest(old,digest):
    need(old['release']==RELEASE and old['adapter_revision']=='r8','original R8 manifest')
    need(set(old['modules'])=={USB,'samurai-mp2650','samurai-gauge-protection'},'original module set')
    need(old['default_input_cap_ua']==900000 and old['default_charge_cap_ua']==250000 and old['source_budget_enforced'] is True,'original caps')
    target='/lib/modules/'+RELEASE+'/extra/samurai-charging/'+USB+'.ko'
    need(old['modules'][USB]['target']==target and old['installed_files'][target]==old['modules'][USB]['sha256'],'original USB target')
    need(len(digest)==64 and all(c in '0123456789abcdef' for c in digest) and digest!=old['modules'][USB]['sha256'],'new USB digest')
    new=copy.deepcopy(old);new['adapter_revision']=REVISION
    new['modules'][USB]['sha256']=digest;new['installed_files'][target]=digest
    return new
def check_manifest_delta(old,new,digest):need(new==make_manifest(old,digest),'manifest outside single USB/revision delta')
def check_archive(raw,files):
    expected={name.lstrip('/'):data for name,data in files.items()}
    need(len(expected)==2 and MANIFEST.lstrip('/') in expected and set(expected)=={MANIFEST.lstrip('/'),('lib/modules/'+RELEASE+'/extra/samurai-charging/'+USB+'.ko')},'exact two rootfs paths')
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        members=tar.getmembers()
        need(len(members)==2 and len({m.name for m in members})==2 and {m.name for m in members}==set(expected),'payload member set')
        for m in members:
            need(m.isfile() and m.mode==0o600 and m.uid==m.gid==0 and m.uname==m.gname=='root' and m.mtime==0 and not m.pax_headers,'payload metadata')
            need(m.size==len(expected[m.name]) and tar.extractfile(m).read()==expected[m.name],'payload bytes')
def archive(files):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for target,raw in sorted(files.items()):
            info=tarfile.TarInfo(target.lstrip('/'));info.uid=info.gid=0
            info.uname=info.gname='root';info.mode=0o600;info.mtime=0;info.size=len(raw)
            tar.addfile(info,io.BytesIO(raw))
    compressed=io.BytesIO()
    with gzip.GzipFile(filename='',mode='wb',fileobj=compressed,mtime=0) as sink:sink.write(stream.getvalue())
    raw=compressed.getvalue();check_archive(raw,files);return raw
def validate_carrier(receipt,carrier,image):
    need(receipt.get('passed') is True,'completed carrier receipt')
    for key in ['only_Image_file_changed','other_entries_and_contents_exact','all_non_Image_bytes_exact',
                'Image_readback_exact','fsck_readonly_passed','native_DTB_untouched',
                'rootfs_R8_camera_untouched','no_device_or_deployment','parent_inputs_unchanged','parent_mountinfo_unchanged']:
        need(receipt.get(key) is True,'carrier completion: '+key)
    need(image=={'sha256':'f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4','bytes':59243008},'actual Image504 build row')
    need(receipt.get('Image504_sha256')==image['sha256'] and receipt.get('Image504')==image and carrier.get('Image504_sha256')==image['sha256'],'actual carrier Image504 written/read back')
    rollback='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
    need(receipt.get('rollback_logdump_sha256')==rollback and receipt.get('rollback',{}).get('sha256')==rollback and receipt['rollback'].get('bytes')==67108864,'actual saved502 input')
    row={k:carrier['logdump'][k] for k in ['sha256','bytes']}
    need(row['bytes']==67108864 and {k:receipt['candidate'][k] for k in ['sha256','bytes']}==row and receipt.get('logdump_sha256')==row['sha256'] and receipt.get('logdump_bytes')==row['bytes'],'actual carrier output')
    need(receipt.get('actual_phone_502_adoption_claimed') is False,'saved candidate is not phone adoption')
def local_inputs():
    pins=json.loads((HERE/'input-pins.json').read_bytes())
    receipts={name:json.loads(pinned(row).read_bytes()) for name,row in pins['receipts'].items()}
    ko=receipts['USB_link'];image=receipts['Image504_build']['build']
    need(ko['passed'] and ko['module_sha256']=='2691c3ceb6245c7c4999c122f015ad93588dce5928b8cd982a5ac725539c4448','native PM ko')
    need(ko['imports_all_from_Image502_builtin'] and not ko['unresolved_strong_imports'] and ko['strong_import_count']==43 and not ko['diagnostics'],'43 original strong imports')
    need(all(c['terminal'] and c['returncode']==0 for c in ko['commands']),'original module build terminal')
    need(image['passed'] and image['identity']['KBUILD_BUILD_VERSION']=='504' and image['outputs']['arch/arm64/boot/Image']['sha256']=='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4','actual Image504')
    need(image['outputs']['vmlinux.symvers']['sha256']==ko['Image502_exports_sha256'] and image['compatibility']['public_headers_unchanged'] and image['compatibility']['actual_ELF_export_names_exact_502'],'actual504 reuse gates')
    need(image['config_exact_original'] and ko['actual_config_values_exact_Image502'] and ko['generated_autoconf_exact_Image502'],'matching config/autoconf lineage')
    old_raw=pinned(pins['base_manifest']).read_bytes();old=json.loads(old_raw)
    old_usb=pinned(pins['old_USB']).read_bytes();new_usb=pinned(pins['new_USB']).read_bytes()
    need(sha(old_raw)=='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f','original manifest bytes')
    need(sha(old_usb)==old['modules'][USB]['sha256'] and sha(new_usb)==ko['module_sha256'],'USB actual bytes')
    identities={'old':module_identity(old_usb,USB),'new':module_identity(new_usb,USB)}
    need(identities['new']['resident_note_sha256']==ko['module_note_sha256'] and identities['old']['resident_note_sha256']!=identities['new']['resident_note_sha256'],'resident identities')
    kept={}
    for target,row in pins['retained'].items():
        raw=pinned(row).read_bytes();kept[target]=sha(raw)
        if target!='/usr/local/sbin/samurai-usb':need(kept[target]==old['installed_files'][target],'retained original file')
    manager=pinned(pins['retained']['/usr/sbin/samurai-charging']).read_text()
    need('adapter_revision' not in manager,'manager revision compatibility')
    protection_target=old['modules']['samurai-gauge-protection']['target']
    with tarfile.open(pinned(pins['old_protection_archive']),mode='r:gz') as tar:
        entries=[m for m in tar.getmembers() if m.name==protection_target.lstrip('/')]
        need(len(entries)==1 and entries[0].isfile(),'retained protection member')
        protection=tar.extractfile(entries[0]).read()
    need(sha(protection)==old['modules']['samurai-gauge-protection']['sha256'],'retained protection actual bytes')
    kept[protection_target]=sha(protection)
    for name in ['boot','native_DTB','rollback_logdump']:pinned(pins['carriers'][name])
    need(pins['carriers']['boot']['sha256']=='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695','unchanged boot')
    need(pins['carriers']['native_DTB']['sha256']=='9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358','native original topology')
    need(pins['carriers']['rollback_logdump']['sha256']=='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1','future preflight502 rollback candidate')
    carrier=json.loads((HERE/'carrier-input.json').read_bytes())
    carrier_receipt=json.loads(pinned(carrier['receipt']).read_bytes())
    validate_carrier(carrier_receipt,carrier,image['outputs']['arch/arm64/boot/Image'])
    pinned(carrier['logdump'])
    need(carrier['logdump']['bytes']==67108864,'new carrier64MiB')
    tests=json.loads((HERE/'package-verification.json').read_bytes())
    need(tests['passed'] and tests['cohort_source_sha256']==file_sha(Path(__file__)),'affected two-file package tests')
    new=make_manifest(old,sha(new_usb));target=old['modules'][USB]['target']
    check_manifest_delta(old,new,sha(new_usb))
    forward={target:new_usb,MANIFEST:encode(new)};backward={target:old_usb,MANIFEST:old_raw}
    cohort=dict(cohort_id='native-usb-pm-budget504-01',adapter_revision=REVISION,release=RELEASE,
        old_manifest_sha256=sha(old_raw),new_manifest_sha256=sha(forward[MANIFEST]),USB_identities=identities,
        retained_files=kept,protection_identity=module_identity(protection,'samurai-gauge-protection'),
        required_Image504_sha256=carrier['Image504_sha256'],required_logdump={k:v for k,v in carrier['logdump'].items() if k!='path'},
        unchanged_boot_sha256=pins['carriers']['boot']['sha256'],native_DTB_sha256=pins['carriers']['native_DTB']['sha256'],
        rollback=dict(rootfs='exact original R8 USB and manifest in separate archive',
            logdump_sha256=pins['carriers']['rollback_logdump']['sha256'],
            actual_future_preflight_and_saved_guard_required=True,current501_is_not_adopted502=True),
        stage_only_result='staged/runtime_pending',module_hot_unload=False,installed=False,
        prepared502_transaction_reusable=False,new_independent_transaction_required=True,
        policy=dict(default_input_cap_ua=900000,default_charge_cap_ua=250000,source_budget_enforced=True,startup_requested_ma=500),
        scope='native DEVICE/runtime-on-active system PM; no IRQ/flat DT or new protection observer',
        acceptance_pending=['new504 actual boot, original DT and matching new disk/resident USB identity',
            'real DWC consumer to USB-input STATELESS dependency and provider-first PM callbacks',
            'controlled suspend/resume with fresh budget authorization; original limits/protection retained',
            'physical source/icon edge timings; full UDC/DMA and auto/direct_complete unproven'],
        not_runtime_or_type_ABI_attestation=True)
    return cohort,forward,backward
def materialize(cohort,forward,backward):
    OUT.mkdir(mode=0o700,exist_ok=False)
    report=dict(passed=False,installed=False,device_accessed=False,source_sha256=file_sha(Path(__file__)),
        input_pins_sha256=file_sha(HERE/'input-pins.json'),carrier_input_sha256=file_sha(HERE/'carrier-input.json'))
    try:
        blobs={'manifest.json':forward[MANIFEST],'rollback-manifest.json':backward[MANIFEST],
            'cohort.json':encode(cohort),'native-usb-pm-payload.tar.gz':archive(forward),'rollback-r8-payload.tar.gz':archive(backward)}
        for name,raw in blobs.items():
            with (OUT/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        check_archive((OUT/'native-usb-pm-payload.tar.gz').read_bytes(),forward)
        check_archive((OUT/'rollback-r8-payload.tar.gz').read_bytes(),backward)
        report.update(passed=True,files={n:dict(sha256=file_sha(OUT/n),bytes=len(v)) for n,v in blobs.items()},rootfs_member_count=2)
    except BaseException as error:
        report.update(passed=False,error=repr(error),replay_permitted=False);raise
    finally:
        with (OUT/'result.json').open('xb') as f:f.write(encode(report));f.flush();os.fsync(f.fileno())
    return report
def audit(cohort,forward,backward):
    result=json.loads((OUT/'result.json').read_bytes())
    need(result['passed'] and result['source_sha256']==file_sha(Path(__file__)) and result['input_pins_sha256']==file_sha(HERE/'input-pins.json') and result['carrier_input_sha256']==file_sha(HERE/'carrier-input.json'),'original materialization binding')
    for name,row in result['files'].items():need(file_sha(OUT/name)==row['sha256'] and (OUT/name).stat().st_size==row['bytes'],'materialized bytes')
    need((OUT/'cohort.json').read_bytes()==encode(cohort) and (OUT/'manifest.json').read_bytes()==forward[MANIFEST] and (OUT/'rollback-manifest.json').read_bytes()==backward[MANIFEST],'materialized identities')
    check_archive((OUT/'native-usb-pm-payload.tar.gz').read_bytes(),forward);check_archive((OUT/'rollback-r8-payload.tar.gz').read_bytes(),backward)
    return dict(passed=True,phase='read-only-offline-audit',installed=False,device_accessed=False)
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',nargs='?',choices=['check-local','build','audit'],default='check-local');parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    need(args.execute==(args.action=='build'),'only offline build requires --execute')
    cohort,forward,backward=local_inputs()
    if args.action=='build':result=materialize(cohort,forward,backward)
    elif args.action=='audit':result=audit(cohort,forward,backward)
    else:result=dict(passed=True,phase='read-only-input-check',new_manifest_sha256=cohort['new_manifest_sha256'],output_exists=OUT.exists(),installed=False)
    print(json.dumps(result,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
