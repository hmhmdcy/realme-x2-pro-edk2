from pathlib import Path
import tarfile,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';out=Path('/mnt/e/edk2-samurai-out/kernel126');release=json.loads((ref/'kernel-build-validation.json').read_text())['release']
with tarfile.open(out/'staging-receipt-private.tar') as tf:
 items={m.name:tf.extractfile(m).read() for m in tf if m.isfile()};assert all('..' not in Path(n).parts and not Path(n).is_absolute() for n in items)
assert items['staging-boot-id-private.txt'].strip()==(out/'source-boot-id-private.txt').read_bytes().strip() and items['new-release.txt'].decode().strip()==release
assert items['staging-receipt']==b'OLD118_MODULE_DIRECTORY_PRESERVED\nNEW126_770_MODULES_STAGED_NO_LOAD\nBLUETOOTH_RELEASE_PATH_INSTALLED\n'
actual={name.removeprefix('./'):digest for digest,name in (line.split('  ',1) for line in items['new-module-tree.sha256'].decode().splitlines())}
with tarfile.open(out/'modules-k126-private.tar.gz') as tf:
 expected={m.name.removeprefix('lib/modules/'+release+'/'):hashlib.sha256(tf.extractfile(m).read()).hexdigest() for m in tf if m.isfile()}
assert actual==expected and sum(n.endswith('.ko') for n in actual)==770
assert items['old-ipa-still-exact.txt'].count(b': OK')==1 and items['new-bluetooth-script.sha256'].split()[0].decode()==json.loads((ref/'live-staging-assets-validation.json').read_text())['bluetooth_script_sha256']
report=dict(new126_directory_all_files_match_validated_archive=True,new126_module_count=770,release=release,old118_directory_preserved=True,old118_ipa_byte_hash_still_exact=True,bluetooth_release_path_file_hash_exact=True,same118_boot_staged=True,no126_module_loaded_yet=True,phone_mutations_this_phase=['parallel126_module_directory','bluetooth_current_release_path','private_preflash_evidence'],userdata_bulk_flash_or_erase=False)
(ref/'live-staging-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'live-staging-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('K126_LIVE_PARALLEL_770_MODULE_TREE_ALL_FILES_AND_OLD118_PRESERVED_PASS')
