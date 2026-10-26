from pathlib import Path
import difflib,hashlib,json,shutil
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel223');root=Path('/home/cy122/x2pro-linux/libcamera214-root');base=root/'work/libcamera220-built/src/libcamera-v0.7.2'
name='src/libcamera/pipeline/simple/simple.cpp';original=(base/name).read_text();assert hashlib.sha256(original.encode()).hexdigest()=='a2e14dd45dcb4fedff0f967d5cfeaeb54959f0df72019fa024279304d272926b';text=original
old='\tbool metadataRequired;\n\tbool metadataProcessed;\n';assert text.count(old)==1;text=text.replace(old,old+'\tstd::optional<ControlList> sensorControls;\n')
old='''		else
			/*
			 * request->sequence() cannot be retrieved from `buffer' inside
			 * queueBuffers because unique_ptr's make buffer->request() invalid
			 * already here.
			 */
			swIsp_->queueBuffers(request->sequence(), buffer,
					     conversionQueue_.front().outputs);
'''
new='''		else {
			SimpleFrameInfo *info = frameInfo_.find(request->sequence());
			ASSERT(info);

			/* Snapshot before ISP processing can evict the sensor history. */
			uint32_t sequence = frameStartEmitter_
				? buffer->metadata().sequence : request->sequence();
			info->sensorControls = delayedCtrls_->get(sequence);
			LOG(SimplePipeline, Debug)
				<< "Captured request " << request->sequence()
				<< " from sequence " << buffer->metadata().sequence
				<< ", control sequence " << sequence;

			/* The software ISP frame context remains keyed by request. */
			swIsp_->queueBuffers(request->sequence(), buffer,
					     conversionQueue_.front().outputs);
		}
'''
assert text.count(old)==1;text=text.replace(old,new)
old='''	swIsp_->processStats(frame, bufferId,
			     delayedCtrls_->get(frame));'''
new='''	SimpleFrameInfo *info = frameInfo_.find(frame);
	if (!info)
		return;

	ASSERT(info->sensorControls.has_value());
	swIsp_->processStats(frame, bufferId, *info->sensorControls);'''
assert text.count(old)==1;text=text.replace(old,new)
patch='Subject: [PATCH] pipeline: simple: snapshot controls for the captured frame\n\nRequests and captured frames diverge when an application stops queueing\nrequests while internal buffers keep streaming. Resolve the sensor history\nusing the captured sequence when frame-start events are available and keep\na per-request copy until ISP statistics are processed. Preserve the legacy\nnon-frame-start path and the request-keyed IPA context.\n\n---\n'
patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'libcamera-capture-control-snapshot.patch').write_text(patch)
candidate=private/'candidate-source';assert not candidate.exists();p=candidate/name;p.parent.mkdir(parents=True);p.write_text(text)
recipe=root/'work/libcamera223';assert not recipe.exists();shutil.copytree(repo/'linux-port/packages/libcamera',recipe)
patch_name='0014-simple-capture-control-snapshot.patch';(recipe/patch_name).write_text(patch)
apk=(recipe/'APKBUILD').read_text();assert apk.count('pkgrel=7')==1;apk=apk.replace('pkgrel=7','pkgrel=8')
marker='\t0013-simple-refresh-sensor-timing.patch\n';assert apk.count(marker)==1;apk=apk.replace(marker,marker+'\t'+patch_name+'\n')
marker=next(l for l in apk.splitlines(True) if l.rstrip().endswith('  0013-simple-refresh-sensor-timing.patch'));apk=apk.replace(marker,marker+hashlib.sha512(patch.encode()).hexdigest()+'  '+patch_name+'\n');(recipe/'APKBUILD').write_text(apk)
config=root/'work/samurai-camera-config223';assert not config.exists();shutil.copytree(repo/'linux-port/packages/samurai-camera-config',config)
apk=(config/'APKBUILD').read_text();assert apk.count('pkgrel=2')==1;apk=apk.replace('pkgrel=2','pkgrel=3').replace('99990.7.2-r7','99990.7.2-r8');(config/'APKBUILD').write_text(apk)
r=dict(stage=223,candidate_framework='99990.7.2-r8',candidate_config_stack='0.1.0-r3',patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),original_source_sha256=hashlib.sha256(original.encode()).hexdigest(),source_files={name:hashlib.sha256(text.encode()).hexdigest()},paired_sof_driver_required_for_synchronised_capture_path=True,current_product_recipes_and_phone_not_changed=True,all13_prior_patches_and_full_feature_packages_retained=True,manual_control_api_not_added_by_this_patch=True)
(here/'candidate-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
