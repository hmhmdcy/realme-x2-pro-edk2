from pathlib import Path
import difflib,hashlib,json,shutil
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel220');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
records=[]
for rgbw,h,sensorw in [(1920,1088,1928),(2296,1728,2304)]:
 r=json.loads((here/f'exposure-metadata-r6-{rgbw}x{h}-validation.json').read_text());c=r['active_controls'];lines=r['delayed_exposure_lines'];values=r['exposure_metadata_microseconds'];assert len(lines)==len(values)==36
 physical_us=(sensorw+c['horizontal_blanking'])*1000000/c['pixel_rate'];cached_us=2560*1000000/326400000
 assert all(abs(actual-line*cached_us)<1 for actual,line in zip(values,lines))
 records.append(dict(output=[rgbw,h],sensor_line_duration_us=physical_us,reported_conversion_line_duration_us=cached_us,
                     maximum_conversion_error_us=max(abs(value-line*physical_us) for value,line in zip(values,lines)),
                     final_delayed_exposure_lines=lines[-1],final_metadata_us=values[-1],final_expected_us=lines[-1]*physical_us))
assert records[0]['maximum_conversion_error_us']>6900 and records[1]['maximum_conversion_error_us']<1
(here/'metadata-root-cause-validation.json').write_text(json.dumps(dict(stage=220,all72_metadata_values_match_cached_four_mp_timing=True,two_mp_metadata_conversion_wrong=True,four_mp_control_case_matches=True,observations=records,physical_delay_calibration_not_claimed=True),indent=2)+'\n')
base=root/'work/libcamera218';changes={}
for name,old,new in [
 ('include/libcamera/ipa/soft.mojom','struct IPAConfigInfo {\n','struct IPAConfigInfo {\n\tlibcamera.IPACameraSensorInfo sensorInfo;\n'),
 ('src/libcamera/pipeline/simple/simple.cpp','\t\tipa::soft::IPAConfigInfo configInfo;\n\t\tconfigInfo.sensorControls',
  '\t\tipa::soft::IPAConfigInfo configInfo;\n\t\tret = data->sensor_->sensorInfo(&configInfo.sensorInfo);\n\t\tif (ret)\n\t\t\treturn ret;\n\t\tconfigInfo.sensorControls'),
 ('src/ipa/simple/soft_simple.cpp','int IPASoftSimple::configure(const IPAConfigInfo &configInfo)\n{\n\tsensorInfoMap_',
  'int IPASoftSimple::configure(const IPAConfigInfo &configInfo)\n{\n\tif (!configInfo.sensorInfo.pixelRate || !configInfo.sensorInfo.minLineLength) {\n\t\tLOG(IPASoft, Error) << "Invalid sensor timing for software ISP";\n\t\treturn -EINVAL;\n\t}\n\n\tcontext_.sensorInfo = configInfo.sensorInfo;\n\tsensorInfoMap_'),
]:
 before=(base/name).read_text();assert before.count(old)==1,name;after=before.replace(old,new);changes[name]=(before,after)
patch='Subject: [PATCH] ipa: simple: refresh sensor timing when configuring a stream\n\nSensor output size, line length and pixel-array clock can change after IPA\ninitialization. Pass the current sensor information on every configure so\nexposure metadata uses the selected mode, including mode switches.\n\n---\n'
for name,(before,after) in changes.items():patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'libcamera-refresh-sensor-timing.patch').write_text(patch)
candidate=private/'candidate-source';assert not candidate.exists()
for name,(_,after) in changes.items():p=candidate/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(after)
recipe=root/'work/libcamera220';assert not recipe.exists();shutil.copytree(repo/'linux-port/packages/libcamera',recipe)
name='0013-simple-refresh-sensor-timing.patch';(recipe/name).write_text(patch)
text=(recipe/'APKBUILD').read_text();assert text.count('pkgrel=6')==1;text=text.replace('pkgrel=6','pkgrel=7')
marker='\t0012-software-isp-dma-heap-selection.patch\n';assert text.count(marker)==1;text=text.replace(marker,marker+'\t'+name+'\n')
marker=next(l for l in text.splitlines(True) if l.rstrip().endswith('  0012-software-isp-dma-heap-selection.patch'));text=text.replace(marker,marker+hashlib.sha512(patch.encode()).hexdigest()+'  '+name+'\n')
(recipe/'APKBUILD').write_text(text)
config=root/'work/samurai-camera-config220';assert not config.exists();shutil.copytree(repo/'linux-port/packages/samurai-camera-config',config)
text=(config/'APKBUILD').read_text();assert text.count('pkgrel=1')==1;text=text.replace('pkgrel=1','pkgrel=2').replace('99990.7.2-r6','99990.7.2-r7');(config/'APKBUILD').write_text(text)
r=dict(stage=220,candidate_framework='99990.7.2-r7',candidate_config_stack='0.1.0-r2',patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
 source_files={name:hashlib.sha256(after.encode()).hexdigest() for name,(_,after) in changes.items()},
 camera_configuration_payload_and_all_previous_patches_unchanged=True,all_original_feature_packages_retained=True,
 public_canonical_recipes_and_phone_not_changed=True,manual_exposure_api_still_open=True)
(here/'candidate-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
