"""Cancel live frame owners, not stale entries in the conversion queue."""
from pathlib import Path
import difflib,hashlib,json,shutil
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel224');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');base=sdk/'work/libcamera224-built/src/libcamera-v0.7.2'
failed=json.loads((private/'lifecycle-candidate-threaded-host-private.log').read_text());assert failed['program_exit']==-6 and failed['all_formats_restored'] and failed['media_graph_restored'] and failed['sensor_controls_restored']
(private/'lifecycle-candidate-threaded-r9-failed-host-private.log').write_text(json.dumps(failed,indent=2)+'\n')
report=dict(stage=224,rejected_candidate='99990.7.2-r9',client_exit=-6,
 assertion='Request::Private::cancel requires RequestPending; conversion queue retained an already completed RAW request.',
 kernel_taint=0,kernel_fault_delta=failed['fault_delta'],controls_formats_graph_and_pm_restored=True,
 r9_not_deployed=True,fix='Cancel only requests still owned by the live frame map after draining streams; discard queue references without dereferencing completed requests.')
(here/'lifecycle-r9-cancellation-failure-validation.json').write_text(json.dumps(report,indent=2)+'\n')
name='src/libcamera/pipeline/simple/simple.cpp';original=(base/name).read_text();text=original
changes=[
 ('\tvoid clear();','\tstd::vector<Request *> clear();'),
 ('''void SimpleFrames::clear()
{
\tframeInfo_.clear();
}''','''std::vector<Request *> SimpleFrames::clear()
{
\tstd::vector<Request *> requests;
\tfor (const auto &[frame, info] : frameInfo_)
\t\trequests.push_back(info.request);
\tframeInfo_.clear();
\treturn requests;
}'''),
 ('''\twhile (!conversionQueue_.empty()) {
\t\tpipe()->cancelRequest(conversionQueue_.front().request);
\t\tconversionQueue_.pop();
\t}''','''\t/* streamOff() may have completed RAW requests still referenced here. */
\twhile (!conversionQueue_.empty())
\t\tconversionQueue_.pop();

\t/* The frame map owns exactly those requests that are still pending. */
\tfor (Request *request : frameInfo_.clear())
\t\tpipe()->cancelRequest(request);'''),
 ('\tdata->frameInfo_.clear();\n\tdata->clearIncompleteRequests();','\tdata->clearIncompleteRequests();'),
]
for old,new in changes:assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
patch='''Subject: [PATCH] simple: cancel only requests still owned by live frames

Stream-off can complete a RAW request before the conversion queue is
cleared. Cancelling that stale queue entry again asserts, and dereferencing
it could access a request already released by the application. Drop queue
references without dereferencing them, extract pending requests from the
frame map, clear that ownership before callbacks, and cancel each once.

---
'''
patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'libcamera-stop-live-requests.patch').write_text(patch)
out=private/'stop-fix-source'/name;assert not out.exists();out.parent.mkdir(parents=True);out.write_text(text)
recipe=sdk/'work/libcamera224-r10';assert not recipe.exists();shutil.copytree(sdk/'work/libcamera224',recipe)
patchname='0016-simple-stop-live-requests.patch';(recipe/patchname).write_text(patch)
apk=(recipe/'APKBUILD').read_text();assert apk.count('pkgrel=9')==1;apk=apk.replace('pkgrel=9','pkgrel=10');marker='\t0015-simple-raw-only-statistics.patch\n';assert apk.count(marker)==1;apk=apk.replace(marker,marker+'\t'+patchname+'\n')
marker=next(l for l in apk.splitlines(True) if l.rstrip().endswith('  0015-simple-raw-only-statistics.patch'));apk=apk.replace(marker,marker+hashlib.sha512(patch.encode()).hexdigest()+'  '+patchname+'\n');(recipe/'APKBUILD').write_text(apk)
config=sdk/'work/samurai-camera-config224-r10';assert not config.exists();shutil.copytree(sdk/'work/samurai-camera-config224',config)
apk=(config/'APKBUILD').read_text();assert apk.count('pkgrel=4')==1;apk=apk.replace('pkgrel=4','pkgrel=5').replace('99990.7.2-r9','99990.7.2-r10');(config/'APKBUILD').write_text(apk)
proof=dict(stage=224,candidate_framework='99990.7.2-r10',candidate_config_stack='0.1.0-r5',patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),original_sources_sha256={name:hashlib.sha256(original.encode()).hexdigest()},source_files={name:hashlib.sha256(text.encode()).hexdigest()},stop_cleanup_uses_live_request_ownership=True,r9_failed_candidate_artifacts_and_evidence_preserved=True,phone_still_r8_r3=True)
(here/'stop-fix-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
build=(here/'build-r9-candidate.py').read_text()
build=build.replace("snapshot=root/'private/libcamera214-before224'","snapshot=root/'private/libcamera214-before224-r10'").replace("retained=root/'work/libcamera224-built'","retained=root/'work/libcamera224-r10-built'").replace("cache=root/'work/libcamera223-built'","cache=root/'work/libcamera224-built'").replace("recipe=root/'work/libcamera224'","recipe=root/'work/libcamera224-r10'")
build=build.replace('packages224','packages224-r10').replace('packages-config224','packages-config224-r10').replace('samurai-camera-config224','samurai-camera-config224-r10').replace('r9','r10').replace('r4','r5').replace('r8_object_cache_preserved','r9_object_cache_preserved').replace('prior14','prior15').replace('0015-simple-raw-only-statistics.patch','0016-simple-stop-live-requests.patch').replace("here/'candidate-source-validation.json'","here/'stop-fix-source-validation.json'").replace("here/'package-build-validation.json'","here/'r10-package-build-validation.json'")
compile(build,'full-r10-build224','exec');(here/'build-r10-candidate.py').write_text(build)
print(json.dumps(proof))
