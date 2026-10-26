"""Export exact installed R8 charging sources; offline hashes and patch check only."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
MAIN=REF/'charging-management-20261023'
THERMAL=HERE.parent/'thermal-bands-candidate'
V2=HERE.parent/'kernel-v2'
FLOAT=REF/'charging-oem-audit-20261023/source-float-candidate'
USER=HERE.parent/'full-integration-candidate/userspace'
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
BASE=PRIVATE/'r8-source-integration-base'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
readj=lambda p:json.loads(p.read_bytes())
receipts={}
def receipt(p):
    data=readj(p);receipts[str(p.relative_to(REF))]=sha(p.read_bytes());return data
def write(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==raw,'refuse changed export: '+str(path)
    else:path.write_bytes(raw)
def jsonraw(data):return (json.dumps(data,indent=2)+'\n').encode()
def diff(name,before,after):
    return ('diff --git a/'+name+' b/'+name+'\n'+('new file mode 100644\n' if before is None else '')+
        ''.join(difflib.unified_diff(('' if before is None else before).splitlines(True),after.splitlines(True),fromfile='/dev/null' if before is None else 'a/'+name,tofile='b/'+name)))

def main():
    thermal=receipt(MAIN/'thermal-bands-build-result.json');tt=receipt(THERMAL/'test-result.json')
    usb=receipt(MAIN/'source-float-build-result.json');ut=receipt(FLOAT/'test-result.json')
    original=receipt(MAIN/'integrated-build-result.json');user=receipt(USER/'test-result.json')
    payload=receipt(MAIN/'r8-payload-result.json');r7=receipt(MAIN/'r7-payload-result.json')
    update=receipt(MAIN/'r8-update-result.json');handoff=receipt(MAIN/'r8-handoff-result.json')
    dt=receipt(MAIN/'usb-dt-result.json');boot=receipt(MAIN/'usb-boot-result.json')
    restored=receipt(MAIN/'usb-startup-rollback-result.json')
    assert thermal['passed'] and thermal['intree'] and not thermal['configuration_differences'] and tt['passed']
    assert thermal['test_receipt_sha256']==sha((THERMAL/'test-result.json').read_bytes())==payload['source_test_receipt_sha256']
    assert payload['source_build_receipt_sha256']==sha((MAIN/'thermal-bands-build-result.json').read_bytes())
    assert usb['passed'] and not usb['configuration_differences'] and ut['asan_ubsan'] and ut['patch_dry_run_private_copy']
    assert ut['tests'][0]['actual_float_100000_resolves_sdp'] and ut['tests'][0]['candidate_assertions']==12768 and ut['tests'][1]['actual_oem_function_assertions']==14
    assert usb['test_receipt_sha256']==sha((FLOAT/'test-result.json').read_bytes())==r7['source_test_receipt_sha256']
    assert r7['source_build_receipt_sha256']==sha((MAIN/'source-float-build-result.json').read_bytes())
    assert update['passed'] and update['installed_new'] and update['terminal_verified'] and update['worker_exited']
    assert handoff['passed'] and handoff['worker_exited'] and handoff['manifest_sha256']==payload['new_manifest_sha256']=='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
    # Read the manifest only to map exact installed hashes. Never copy private originals.
    installed_raw=(PRIVATE/'r8-candidate/manifest.json').read_bytes();assert sha(installed_raw)==handoff['manifest_sha256']
    installed=json.loads(installed_raw);assert installed['adapter_revision']=='r8'
    source_rows={};kernel={};rootfs={}
    def source(path,target,expected,origin,collection):
        raw=path.read_bytes();assert sha(raw)==expected,str(path)
        collection[target]=raw
        source_rows[target]={'sha256':expected,'bytes':len(raw),'origin':str(path.relative_to(REF)),'evidence':origin}
    changed={'samurai-mp2650.c','mp2650-core.h','oem-full-cycle.h','thermal-bands.h'}
    assert changed<=set(tt['files'])
    for name,digest in thermal['sources'].items():
        src=(THERMAL if name in changed else V2)/name
        source(src,'drivers/power/supply/'+name,digest,'thermal-bands-build-result.json sources',kernel)
    for name,digest in usb['sources'].items():
        source((MAIN if name.endswith('.c') else FLOAT)/name,'drivers/power/supply/'+name,digest,'source-float-build-result.json sources',kernel)
    protect='samurai-gauge-protection.c'
    source(MAIN/protect,'drivers/power/supply/'+protect,original['sources'][protect],'integrated-build-result.json protection source and module',kernel)
    expected_modules={
        'samurai-mp2650':thermal['module_sha256'],
        'samurai-usb-input':usb['module_sha256'],
        'samurai-gauge-protection':original['modules']['samurai-gauge-protection']['sha256']}
    for name,digest in expected_modules.items():assert installed['modules'][name]['sha256']==digest
    assert user['passed'] and user['candidate_files']['samurai-charging.py']==update['service_read_only_sha256']=='61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
    service_sources={'usr/sbin/samurai-charging':USER/'samurai-charging.py','etc/init.d/samurai-charging':MAIN/'samurai-charging.openrc',
        'usr/lib/samurai-charging/control-trial.py':MAIN/'control-trial.py','usr/lib/samurai-charging/live-session.py':MAIN/'live-session.py'}
    for target,path in service_sources.items():source(path,target,installed['installed_files']['/'+target],'R8 installed manifest + unchanged service dependency',rootfs)
    for target,raw in kernel.items():write(HERE/'kernel-sources'/target,raw)
    for target,raw in rootfs.items():write(HERE/'rootfs-sources'/target,raw)
    # Check quoted local headers are complete; Linux/system headers stay in the base tree.
    for name,raw in kernel.items():
        for include in re.findall(r'^#include "([^"/]+)"',raw.decode(),re.M):assert 'drivers/power/supply/'+include in kernel,(name,include)
    old_patch=(MAIN/'kernel-integration.patch').read_text()
    previous=receipt(MAIN/'kernel-integration-result.json');assert sha((MAIN/'kernel-integration.patch').read_bytes())==previous['patch_sha256']
    chunks={part.split(' b/',1)[0]:'diff --git '+part for part in old_patch.split('diff --git ')[1:]}
    cached_base=readj(BASE/'manifest.json');assert cached_base['commit']=='ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
    base_expected={row['path']:row for row in cached_base['files']}
    integration_paths=['drivers/power/supply/Makefile','drivers/power/supply/Kconfig','arch/arm64/boot/dts/qcom/sm8150-samurai.dts']
    before={};after={};basis={}
    for name in integration_paths:
        chunk=chunks['a/'+name]
        lines=chunk.splitlines(True);hunks=[i for i,line in enumerate(lines) if line.startswith('@@')];assert len(hunks)==1
        body=lines[hunks[0]+1:];assert all(line[:1] in [' ','+'] for line in body)
        context=''.join(line[1:] for line in body if line.startswith(' '));addition=''.join(line[1:] for line in body if line.startswith('+'))
        cached=BASE/name.replace('/','--');blob=cached.read_text()
        assert len(cached.read_bytes())==base_expected[name]['bytes'] and sha(cached.read_bytes())==base_expected[name]['sha256']
        assert addition.strip() not in blob
        basis[name]={'kind':'fixed Image363 Git blob read from root-provided cache','revision':cached_base['commit'],'sha256':sha(cached.read_bytes()),'full_base_file':True}
        before[name]=blob;after[name]=blob+addition
    kernel_patch=''.join(diff(name,None,raw.decode()) for name,raw in kernel.items())
    kernel_patch+=''.join(diff(name,before[name],after[name]) for name in integration_paths[:2])
    native_patch=diff(integration_paths[2],before[integration_paths[2]],after[integration_paths[2]])
    write(HERE/'kernel-integration.patch',kernel_patch.encode());write(HERE/'native-usb-supply.patch',native_patch.encode())
    fragment='CONFIG_CHARGER_SAMURAI_MP2650=m\nCONFIG_SAMURAI_USB_INPUT=m\nCONFIG_BATTERY_SAMURAI_GAUGE_PROTECTION=m\n'
    write(HERE/'kernel-config.fragment',fragment.encode())
    # Real patch command and resulting full new-file bytes, in a fresh disposable tree.
    logs=[]
    with tempfile.TemporaryDirectory(prefix='r8-source-patch-') as tmp:
        root=Path(tmp)
        for name,raw in before.items():p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(raw)
        for patch in ['kernel-integration.patch','native-usb-supply.patch']:
            args=['patch','--batch','--fuzz=0','-p1','-d',str(root),'-i',str(HERE/patch)]
            dry=subprocess.run(args+['--dry-run'],capture_output=True,text=True);assert dry.returncode==0,dry.stdout+dry.stderr
            applied=subprocess.run(args,capture_output=True,text=True);assert applied.returncode==0,applied.stdout+applied.stderr
            logs.append({'patch':patch,'dry_run_returncode':dry.returncode,'apply_returncode':applied.returncode,'fuzz':0})
        for name,raw in kernel.items():assert (root/name).read_bytes()==raw
        for name,text in after.items():assert (root/name).read_text()==text
    check={'passed':True,'new_kernel_files_exact':len(kernel),'patch_commands':logs,'base_files':basis,
        'all_three_full_base_blobs_checked':all(b['full_base_file'] for b in basis.values()),'full_kernel_tree_checked':False,'compiled':False,'old_tests_rerun':False,
        'shared_worktree_read':False,'shared_build_read':False,'git_index_used':False,'phone_accessed':False,'sdk_invoked':False}
    write(HERE/'patch-check-result.json',jsonraw(check))
    assert dt['passed'] and dt['dtb_sha256']==boot['dtb_sha256']=='c559d2c4c9a83e85473b1b24724bb8938f1084bd3efcae9c4b67f37c2a4c4503'
    assert dt['all_other_properties_byte_exact'] and boot['kernel_image_preserved']=='15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'
    startup=[]
    assert restored['MaxPower_ma']==100 and restored['native_allowance_ua']==100000
    for row in restored['restored']:startup.append({'installed_path':row['path'],'sha256':row['sha256'],'source_copied':False,'evidence':'usb-startup-rollback-result.json'})
    # Describe public repository creation paths without replacing the platform recipe.
    repository_usb={}
    for rel in ['linux-port/scripts/samurai-usb.sh','linux-port/packages/samurai-platform/usr_sbin_samurai-usb']:
        p=REF.parents[0]/rel;raw=p.read_bytes();assert re.search(rb'echo 100 >',raw) and not re.search(rb'echo 500 >',raw)
        repository_usb[rel]={'sha256':sha(raw),'declared_MaxPower_ma':100,'copied_or_modified':False}
    manifest={'schema':'samurai-r8-charging-source-integration-v1','adapter_revision':'r8','scope':'exact deployed charging source layer only; existing Image/platform remain external',
        'release':installed['release'],'installed_manifest_sha256':sha(installed_raw),'installed_modules_sha256':expected_modules,
        'loaded_note_sha256':handoff['loaded_notes_sha256'],'sources':source_rows,'source_receipts_sha256':receipts,
        'patches':{n:sha((HERE/n).read_bytes()) for n in ['kernel-integration.patch','native-usb-supply.patch','kernel-config.fragment']},
        'base_files':basis,'current_boot':{'image_sha256':boot['kernel_image_preserved'],'native_dtb_sha256':dt['dtb_sha256'],'boot_sha256':boot['boot_sha256'],'DT_source_patch_is_not_deployed_DTB':True},
        'requests':{'input_cap_ua':900000,'charge_cap_ua':250000,'inherited_per_cell_cv_ceiling_uv':4362500,'source_budget_enforced':True},
        'usb_startup':{'MaxPower_ma':100,'installed_scripts':startup,'repository_creation_paths':repository_usb,'MaxPower_is_not_source_authorization':True},
        'last_r8_handoff_source':{'type':'SDP','native_ua':handoff['limits']['native_ua'],'source_budget_ua':handoff['limits']['source_budget_ua'],'effective_input_ua':handoff['limits']['input_ua']},
        'unaccepted':['physical temperature boundaries','physical Full/recharge cycle','screen charging icon latency','SDP500 authorization','PM resume failure resolution'],
        'excluded':['USBIN init helper','APSD rerun','EUD changes','PHY window','DWC window or resume candidates','USB500 trial','PM tools/WIP','camera/BT/platform recipe'],
        'private_originals_copied':False,'module_binaries_copied':False,'private_identity_copied':False,'phone_accessed':False,'sdk_invoked':False,'image_built':False}
    write(HERE/'source-manifest.json',jsonraw(manifest))
    print(json.dumps({'passed':True,'kernel_files':len(kernel),'rootfs_files':len(rootfs),'three_full_base_blobs_checked':check['all_three_full_base_blobs_checked'],'manifest_sha256':sha((HERE/'source-manifest.json').read_bytes())}))

if __name__=='__main__':main()
