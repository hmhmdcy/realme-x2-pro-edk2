"""Enable RAW-only statistics using the existing CPU statistics implementation."""
from pathlib import Path
import difflib,hashlib,json,shutil

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel224');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');base=sdk/'work/libcamera223-built/src/libcamera-v0.7.2'
files={};original={}
def edit(name,old,new):
 if name not in files:original[name]=(base/name).read_text();files[name]=original[name]
 assert files[name].count(old)==1,(name,old,files[name].count(old))
 files[name]=files[name].replace(old,new)
edit('src/libcamera/software_isp/debayer.h',
 '\tvirtual const SharedFD &getStatsFD() = 0;',
 '\tvirtual const SharedFD &getStatsFD() = 0;\n\tvirtual bool supportsInputStatsOnly() const { return false; }')
edit('src/libcamera/software_isp/debayer_cpu.h',
 '\tconst SharedFD &getStatsFD() override { return stats_->getStatsFD(); }',
 '\tconst SharedFD &getStatsFD() override { return stats_->getStatsFD(); }\n\tbool supportsInputStatsOnly() const override { return true; }')
edit('src/libcamera/software_isp/debayer_cpu.h','\tbool ccmEnabled_;','\tbool statsOnly_ = false;\n\tbool ccmEnabled_;')
edit('src/libcamera/software_isp/debayer_cpu.cpp',
 '\tinputConfig_.stride = inputCfg.stride;\n\n\tif (outputCfgs.size() != 1)',
 '''\tinputConfig_.stride = inputCfg.stride;

\tstatsOnly_ = outputCfgs.empty();
\tif (statsOnly_) {
\t\twindow_ = Rectangle(inputCfg.size);
\t\tstats_->setWindow(window_);
\t\tLOG(Debayer, Info) << "RAW-only CPU statistics enabled";
\t\treturn 0;
\t}

\tif (outputCfgs.size() != 1)''')
edit('src/libcamera/software_isp/debayer_cpu.cpp',
 '\tdmaSyncBegin(dmaSyncers, input, output);\n\n\tupdateLookupTables(params);',
 '''\tdmaSyncBegin(dmaSyncers, input, output);

\tif (statsOnly_) {
\t\tASSERT(!output);
\t\tMappedFrameBuffer in(input, MappedFrameBuffer::MapFlag::Read);
\t\tif (!in.isValid() || in.planes().empty() ||
\t\t    in.planes()[0].size() < size_t(inputConfig_.stride) * inputSize_.height) {
\t\t\tLOG(Debayer, Error) << "Invalid RAW statistics input buffer";
\t\t\tinput->_d()->metadata().status = FrameMetadata::FrameError;
\t\t} else {
\t\t\tstats_->processFrame(frame, 0, in);
\t\t}
\t\tdmaSyncers.clear();
\t\tinputBufferReady.emit(input);
\t\treturn;
\t}

\tupdateLookupTables(params);''')
edit('include/libcamera/internal/software_isp/software_isp.h',
 '\tbool isValid() const;', '\tbool isValid() const;\n\tbool supportsInputStatsOnly() const;')
edit('include/libcamera/internal/software_isp/software_isp.h',
 '\tbool ccmEnabled_;','\tbool statsOnly_ = false;\n\tbool ccmEnabled_;')
edit('src/libcamera/software_isp/software_isp.cpp',
 'int SoftwareIsp::configure(const StreamConfiguration &inputCfg,',
 '''bool SoftwareIsp::supportsInputStatsOnly() const
{
\treturn debayer_ && debayer_->supportsInputStatsOnly();
}

int SoftwareIsp::configure(const StreamConfiguration &inputCfg,''')
edit('src/libcamera/software_isp/software_isp.cpp',
 '\tret = debayer_->configure(inputCfg, outputCfgs, ccmEnabled_);\n\tif (ret < 0)\n\t\treturn ret;',
 '\tret = debayer_->configure(inputCfg, outputCfgs, ccmEnabled_);\n\tif (ret < 0)\n\t\treturn ret;\n\tstatsOnly_ = outputCfgs.empty();')
edit('src/libcamera/software_isp/software_isp.cpp',
 '''\t/*
\t * Validate the outputs as a sanity check: at least one output is
\t * required, all outputs must reference a valid stream.
\t */''',
 '''\t/* RAW-only statistics hold the input until CPU reads have finished. */
\tif (statsOnly_) {
\t\tif (!outputs.empty())
\t\t\treturn -EINVAL;
\t\tqueuedInputBuffers_.push_back(input);
\t\tprocess(frame, input, nullptr);
\t\treturn 0;
\t}

\t/* Converted output requires one valid stream and buffer. */''')
edit('src/libcamera/pipeline/simple/simple.cpp',
 '\tif (outputCfgs.empty())\n\t\treturn 0;',
 '''\tif (outputCfgs.empty()) {
\t\tif (!data->rawStream_ || !data->swIsp_ ||
\t\t    !data->swIsp_->supportsInputStatsOnly())
\t\t\treturn 0;
\t\tdata->useConversion_ = true;
\t}''')
edit('src/libcamera/pipeline/simple/simple.cpp',
 '\tbool metadataRequired = false;', '\tbool metadataRequired = data->useConversion_ && !!data->swIsp_;')
edit('src/libcamera/pipeline/simple/simple.cpp',
 '''\t\t/* Complete the input buffer as with raw-only processing. */
\t\tRequest *request = buffer->request();''',
 '''\t\t/* Complete RAW only after statistics have released its input. */
\t\tRequest *request = buffer->request();
\t\tif (buffer->metadata().status != FrameMetadata::FrameSuccess) {
\t\t\tSimpleFrameInfo *info = frameInfo_.find(request->sequence());
\t\t\tif (info)
\t\t\t\tinfo->metadataRequired = false;
\t\t}''')
patch='''Subject: [PATCH] simple: run CPU statistics for RAW-only requests

Keep RAW buffers unmodified, but hold them while the existing CPU statistics
reader gathers samples. Configure and run the software IPA so RAW-only
requests receive exposure/gain metadata and automatic sensor updates.
Allocate no converted output buffers. Gate this path on explicit CPU
support and preserve the existing non-CPU direct RAW path. Complete input
errors without waiting for metadata that could not be produced.

---
'''
for name,text in files.items():
 patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(original[name].splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'libcamera-raw-only-statistics.patch').write_text(patch)
out=private/'candidate-source';assert not out.exists()
for name,text in files.items():p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
recipe=sdk/'work/libcamera224';assert not recipe.exists();shutil.copytree(repo/'linux-port/packages/libcamera',recipe)
name='0015-simple-raw-only-statistics.patch';(recipe/name).write_text(patch)
apk=(recipe/'APKBUILD').read_text();assert apk.count('pkgrel=8')==1;apk=apk.replace('pkgrel=8','pkgrel=9');marker='\t0014-simple-capture-control-snapshot.patch\n';assert apk.count(marker)==1;apk=apk.replace(marker,marker+'\t'+name+'\n')
marker=next(l for l in apk.splitlines(True) if l.rstrip().endswith('  0014-simple-capture-control-snapshot.patch'));apk=apk.replace(marker,marker+hashlib.sha512(patch.encode()).hexdigest()+'  '+name+'\n');(recipe/'APKBUILD').write_text(apk)
config=sdk/'work/samurai-camera-config224';assert not config.exists();shutil.copytree(repo/'linux-port/packages/samurai-camera-config',config)
apk=(config/'APKBUILD').read_text();assert apk.count('pkgrel=3')==1;apk=apk.replace('pkgrel=3','pkgrel=4').replace('99990.7.2-r8','99990.7.2-r9');(config/'APKBUILD').write_text(apk)
r=dict(stage=224,candidate_framework='99990.7.2-r9',candidate_config_stack='0.1.0-r4',patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
 original_sources_sha256={n:hashlib.sha256(t.encode()).hexdigest() for n,t in original.items()},source_files={n:hashlib.sha256(t.encode()).hexdigest() for n,t in files.items()},
 prior14_patches_and_full_features_preserved=True,cpu_raw_statistics_no_output_buffers=True,raw_buffer_read_only_dma_synced=True,
 raw_capture_control_snapshots_and_ipa_lifecycle_enabled=True,unsupported_non_cpu_raw_path_preserved=True,
 manual_api_not_yet_implemented=True,phone_and_canonical_recipe_not_modified=True)
(here/'candidate-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
