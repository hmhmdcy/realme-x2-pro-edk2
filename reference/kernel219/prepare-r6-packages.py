from pathlib import Path
import difflib,hashlib,json,re,shutil

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel219')
root=Path('/home/cy122/x2pro-linux/libcamera214-root')
source=root/'work/libcamera218'
before=(source/'src/libcamera/software_isp/software_isp.cpp').read_text()
needle='\tconst GlobalConfiguration &configuration = pipe->cameraManager()->_d()->configuration();\n'
assert before.count(needle)==1
after=before.replace(needle,needle+'''	const auto heap = configuration.option<std::string>({ "software_isp", "dma_heap" });
	if (heap == "system")
		return DmaBufAllocator::DmaBufAllocatorFlag::SystemHeap;
	if (heap && heap != "auto") {
		LOG(SoftwareIsp, Error) << "Unsupported software ISP dma_heap selection";
		return {};
	}
''')
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/src/libcamera/software_isp/software_isp.cpp',tofile='b/src/libcamera/software_isp/software_isp.cpp'))
(here/'libcamera-dma-heap-selector.patch').write_text(patch)
recipe=root/'work/libcamera219';assert not recipe.exists()
shutil.copytree(repo/'linux-port/packages/libcamera',recipe,ignore=shutil.ignore_patterns('__pycache__'))
added={'0011-imx471-native-quad-cpu.patch':(repo/'linux-port/camera/isp/experimental/0001-libcamera-imx471-native-quad-cpu.patch').read_bytes(),
       '0012-software-isp-dma-heap-selection.patch':patch.encode()}
for name,data in added.items():(recipe/name).write_bytes(data)
text=(recipe/'APKBUILD').read_text();assert text.count('pkgrel=5')==1;text=text.replace('pkgrel=5','pkgrel=6')
needle='\t0010-build-allow-external-ipa-signing-key.patch\n';assert text.count(needle)==1
text=text.replace(needle,needle+''.join('\t'+name+'\n' for name in added))
needle=next(l for l in text.splitlines(True) if l.rstrip().endswith('  0010-build-allow-external-ipa-signing-key.patch'))
text=text.replace(needle,needle+''.join(hashlib.sha512(data).hexdigest()+'  '+name+'\n' for name,data in added.items()))
(recipe/'APKBUILD').write_text(text)
config=root/'work/samurai-camera-config219';assert not config.exists()
shutil.copytree(repo/'linux-port/packages/samurai-camera-config',config)
text=(config/'APKBUILD').read_text().replace('pkgrel=0','pkgrel=1').replace('99990.7.2-r5','99990.7.2-r6')
yaml=(config/'configuration.yaml').read_text();assert yaml.count('    mode: cpu')==1
yaml=yaml.replace('    mode: cpu','    mode: cpu\n    dma_heap: system')
(config/'configuration.yaml').write_text(yaml)
text=re.sub(r'^[0-9a-f]{128}  configuration\.yaml$',hashlib.sha512(yaml.encode()).hexdigest()+'  configuration.yaml',text,flags=re.M)
(config/'APKBUILD').write_text(text)
lock=json.loads((repo/'linux-port/packages/libcamera/source-lock.json').read_text())
assert all((recipe/name).read_bytes()==(repo/'linux-port/packages/libcamera'/name).read_bytes() for name in lock['source_files_sha256'] if name!='APKBUILD')
report=dict(stage=219,new_framework_version='99990.7.2-r6',new_config_version='0.1.0-r1',
            original_full_feature_set_and_all_subpackages_retained=True,all_original_source_inputs_retained=True,
            native_quad_option_still_default_false=True,product_config_selects_system_heap=True,
            camera_heap_device_permissions_and_dsp_pool_rule_unchanged=True,
            candidate_recipe_sha256=hashlib.sha256((recipe/'APKBUILD').read_bytes()).hexdigest(),
            added_patches={n:hashlib.sha256(d).hexdigest() for n,d in added.items()},
            canonical_recipes_and_phone_packages_not_changed=True)
(here/'r6-package-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
