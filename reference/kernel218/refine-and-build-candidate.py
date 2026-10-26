from pathlib import Path
import difflib,hashlib,json,os,subprocess,time

os.umask(0o077)
here=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel218')
root=Path('/home/cy122/x2pro-linux/libcamera214-root')
src=root/'work/libcamera218';original=root/'work/libcamera/src/libcamera-v0.7.2'
assert (private/'candidate-build-private.log').is_file()
assert not (private/'candidate-build-r2-private.log').exists()
path=src/'src/libcamera/software_isp/debayer_cpu.cpp';text=path.read_text()
start=text.index('\t/* Adjust src to top left corner of the window */',text.index('void DebayerCpuThread::process('))
end=text.index('\t}\n\n\tdebayer_->workPendingMutex_',start)
text=text[:start]+''.join('\t'+line if line.strip() else line for line in text[start:end].splitlines(True))+text[end:]
text=text.replace('metadata.planes()[0].bytesused = out.planes()[0].size();','metadata.planes()[0].bytesused = nativeQuad_ ? outputConfig_.frameSize : out.planes()[0].size();')
path.write_text(text)
path=src/'src/libcamera/software_isp/software_isp.cpp';text=path.read_text().replace('const bool nativeQuadExperiment =','[[maybe_unused]] const bool nativeQuadExperiment =');path.write_text(text)
assert (src/'include/libcamera/internal/software_isp/swisp_stats.h').exists()
(src/'test/native-quad-cpu.cpp').write_text((here/'native-quad-cpu-test.cpp').read_text())
path=src/'test/meson.build';text=path.read_text();old="    {'name': 'native-quad', 'sources': ['native-quad.cpp'], 'dependencies': [libthreads]},";assert text.count(old)==1
text=text.replace(old,old+"\n    {'name': 'native-quad-cpu', 'sources': ['native-quad-cpu.cpp'], 'dependencies': [libthreads]},");path.write_text(text)
proof=json.loads((here/'candidate-source-validation.json').read_text())
names=sorted(set(proof['files'])|{'test/native-quad-cpu.cpp'})
patch=''
for name in names:
    before=(original/name).read_text() if (original/name).exists() else ''
    after=(src/name).read_text()
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    proof['files'][name]=hashlib.sha256(after.encode()).hexdigest()
(here/'libcamera-native-quad-candidate.patch').write_text(patch)
(here/'candidate-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
command=['chroot',str(root),'/usr/bin/ninja','-C','/work/libcamera218/output','-j4',
         'src/libcamera/libcamera.so.0.7.2','test/native-quad','test/native-quad-cpu','test/quad-bayer','test/bayer-format']
with (private/'candidate-build-r2-private.log').open('wb') as output:
    process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
    (private/'active-build-private.json').write_text(json.dumps(dict(pid=process.pid,command=command,started=time.time()),indent=2)+'\n')
    code=process.wait(timeout=3600)
assert code==0,'Inspect existing r2 build; do not restart from scratch'
report=dict(stage=218,candidate_simple_virtual_cpu_egl_build_passed=True,compiler_warnings_as_errors=True,
            focused_native_quad_cpu_quad_bayer_format_tests_built=True,broad_all_target_build_stopped_intentionally=True,
            production_full_feature_packages_unchanged=True,no_package_device_install=True)
(here/'candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
