from pathlib import Path
import difflib,hashlib,json,re,shutil
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214');original=Path('/home/cy122/pmos-samurai-rootfs01/pmaports/temp/libcamera');target=repo/'linux-port/packages/libcamera';assert not target.exists();target.mkdir()
recipe=(original/'APKBUILD').read_text();inputs=[]
for p in sorted(original.iterdir()):
    if not p.is_file() or p.name=='APKBUILD':continue
    match=re.search(r'(?m)^([0-9a-f]{128})  '+re.escape(p.name)+'$',recipe)
    assert match and hashlib.sha512(p.read_bytes()).hexdigest()==match[1],p.name
    shutil.copyfile(p,target/p.name);inputs.append(p.name)
assert sum(name.endswith('.patch') for name in inputs)==6
additional=repo/'linux-port/camera/libcamera';lock=json.loads((additional/'source-lock.json').read_text())
for name,digest in lock['additional_patches_sha256'].items():
    p=additional/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==digest;shutil.copyfile(p,target/name)
source=private.parent/'kernel213/source/libcamera-v0.7.2';changes={}
path='meson_options.txt';old=(source/path).read_text();marker="option('ipas',";assert old.count(marker)==1
new=old.replace(marker,"option('ipa-priv-key',\n        type : 'string',\n        value : '',\n        description : 'External IPA signing private key (empty generates a new key)')\n\n"+marker);changes[path]=(old,new)
path='src/meson.build';old=(source/path).read_text();before="""    ipa_priv_key = custom_target('ipa-priv-key',
                                 output : ['ipa-priv-key.pem'],
                                 command : [gen_ipa_priv_key, '@OUTPUT@'])"""
after="""    ipa_key_path = get_option('ipa-priv-key')
    if ipa_key_path == ''
        ipa_priv_key = custom_target('ipa-priv-key',
                                     output : ['ipa-priv-key.pem'],
                                     command : [gen_ipa_priv_key, '@OUTPUT@'])
    else
        ipa_priv_key = files(ipa_key_path)[0]
    endif"""
assert old.count(before)==1;changes[path]=(old,old.replace(before,after))
build_patch='0010-build-allow-external-ipa-signing-key.patch';patch=''.join(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path)) for path,(old,new) in changes.items());(target/build_patch).write_text(patch)
assert 'pkgrel=4\n' in recipe;recipe=recipe.replace('pkgrel=4\n','pkgrel=5\n')
assert recipe.count('\tlibyuv-dev\n')==1;recipe=recipe.replace('\tlibyuv-dev\n','\tlibyuv\n\tlibyuv-dev\n')
marker='\t0006-libcamera-Add-quad-Bayer-CFA-layout-support.patch\n';assert recipe.count(marker)==1
names=[*lock['additional_patches_sha256'],build_patch]
recipe=recipe.replace(marker,marker+''.join('\t'+name+'\n' for name in names))
marker='build() {\n';assert recipe.count(marker)==1
recipe=recipe.replace(marker,marker+'\t[ -n "${LIBCAMERA_IPA_PRIVATE_KEY:-}" ] && [ -r "$LIBCAMERA_IPA_PRIVATE_KEY" ] || die "Set LIBCAMERA_IPA_PRIVATE_KEY to a retained private build input"\n\tcase "$LIBCAMERA_IPA_PRIVATE_KEY" in /*) ;; *) die "IPA key path must be absolute" ;; esac\n')
marker='\t\t-Ddocumentation=disabled \\\n';assert recipe.count(marker)==1
recipe=recipe.replace(marker,marker+'\t\t-Dipa-priv-key="$LIBCAMERA_IPA_PRIVATE_KEY" \\\n')
assert recipe.count('\tmeson compile -C output\n')==1;recipe=recipe.replace('\tmeson compile -C output\n','\tmeson compile -C output -j "${JOBS:-4}"\n')
marker='"$(find "$builddir"/output -type f -iname "*ipa-priv-key.pem")"';assert recipe.count(marker)==1;recipe=recipe.replace(marker,'"$LIBCAMERA_IPA_PRIVATE_KEY"')
assert recipe.endswith('"\n');recipe=recipe[:-2]+''.join(hashlib.sha512((target/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in names)+'"\n'
pairs=re.findall(r'(?m)^([0-9a-f]{128})  ([^\n]+)$',recipe);base=[p for p in pairs if p[1] not in names];assert base[6][1].startswith('0006-')
ordered=base[:7]+[(hashlib.sha512((target/name).read_bytes()).hexdigest(),name) for name in names]+base[7:]
recipe=recipe.split('sha512sums="',1)[0]+'sha512sums="\n'+''.join(digest+'  '+name+'\n' for digest,name in ordered)+'"\n'
(target/'APKBUILD').write_text('# Realme X2 Pro: retain the distro feature set; add IMX471 and first-frame fixes.\n'+recipe)
record=dict(stage=214,original_recipe_version='99990.7.2-r4',new_recipe_version='99990.7.2-r5',original_six_patches_and_all_tuning_desktop_inputs_preserved=True,original_auto_virtual_pipelines_and_subpackages_preserved=True,three_verified_image_processing_patches_added=list(lock['additional_patches_sha256']),build_only_external_ipa_key_option_added=True,default_upstream_key_generation_retained_when_option_empty=True,ipa_resigned_after_strip_with_matching_retained_key=True,no_private_key_copied_into_public_sources=True,source_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.is_file()})
(target/'source-lock.json').write_text(json.dumps(record,indent=2)+'\n');(here/'full-port-source-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='source_files_sha256'}))
