"""Reset retired output IO before starting a newly negotiated camera pool."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel264');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire264-reset-output';assert not W.exists();W.mkdir()
base=SDK/'work/pipewire262/pipewire-1.6.9/spa/plugins/libcamera';source=W/'source';shutil.copytree(base,source)
q=subprocess.run(['patch','--silent','-p4','-d',str(source)],input=(R.parent/'kernel263/libcamera-broadcast-ownership-candidate.patch').read_bytes(),capture_output=True);assert q.returncode==0,q.stderr
p=source/'libcamera-source.cpp';s=p.read_text();(P/'spa-broadcast-before-reset-private.cpp').write_text(s)
needle='''	if (impl->active)
		return 0;

	spa_log_info(impl->log, "starting camera %s", impl->camera->id().c_str());'''
assert s.count(needle)==1
s=s.replace(needle,'''\tif (impl->active)
		return 0;

	/* A retained IO area can still describe a frame from the retired pool.
	 * Publish no buffer until this run receives its first completed request. */
	if (port->io) {
		spa_log_info(impl->log, "reset output IO before start status:%d id:%u",
			port->io->status, port->io->buffer_id);
		*port->io = SPA_IO_BUFFERS_INIT;
	}
	spa_log_info(impl->log, "starting camera %s", impl->camera->id().c_str());''')
p.write_text(s);original=(base/'libcamera-source.cpp').read_text()
(R/'libcamera-reset-output-io-candidate.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/spa/plugins/libcamera/libcamera-source.cpp',tofile='b/spa/plugins/libcamera/libcamera-source.cpp')))
prefix='/work/pipewire264-reset-output'
common=['g++','-std=c++20','-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-missing-field-initializers','-I'+prefix+'/source','-I/work/pipewire262/sdk/usr/include/spa-0.2','-I/candidate238-r14/usr/include/libcamera']
q=subprocess.run(['chroot',str(SDK),*common,'-c',prefix+'/source/libcamera-source.cpp','-o',prefix+'/libcamera-source.cpp.o'],capture_output=True)
(P/'reset-output-spa-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-2500:]
objects=[prefix+'/libcamera-source.cpp.o']+['/'+str(p.relative_to(SDK)) for p in sorted((SDK/'work/pipewire263-automatic').glob('*.o')) if p.name!='libcamera-source.cpp.o']
q=subprocess.run(['chroot',str(SDK),'g++','-shared',*objects,'-L/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-pthread','-o',prefix+'/libspa-libcamera.so'],capture_output=True);(P/'reset-output-spa-link-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
shutil.copyfile(W/'libspa-libcamera.so',P/'libspa-libcamera-reset-output.so')
report=dict(stage=264,compiled=True,source_sha256=hashlib.sha256(s.encode()).hexdigest(),spa_sha256=hashlib.sha256((P/'libspa-libcamera-reset-output.so').read_bytes()).hexdigest(),core_sha256=json.loads((R/'proxy-only-build-validation.json').read_text())['core_sha256'],busy_counters_never_reset=True,no_system_deployment=True)
(R/'reset-output-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
