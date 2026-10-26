"""Refresh camera-owned image storage when graph metadata is rebound."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
import host
R=Path(__file__).parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-fresh-allocation';assert not W.exists();W.mkdir()
base=SDK/'work/pipewire264-reset-output/source';source=W/'source';shutil.copytree(base,source);p=source/'libcamera-source.cpp';s=p.read_text();assert hashlib.sha256(s.encode()).hexdigest()=='b8984e923da6cf8823282abe523e7aeeeb35bd99fd70b88744a3aff2899c5bf5'
needle='''\tif (port->n_buffers) {
\t\tspa_libcamera_stream_off(impl);
\t\tif ((res = spa_libcamera_clear_buffers(port)) < 0)
\t\t\treturn res;
\t}'''
assert s.count(needle)==1
s=s.replace(needle,'''    if (port->n_buffers) {
        spa_libcamera_stream_off(impl);
        if ((res = spa_libcamera_clear_buffers(port)) < 0)
            return res;

        /* Busy metadata belongs to a graph allocation. Rebinding that
         * metadata must not expose the same camera image storage while an
         * old consumer can still retain an fd for it. Allocate fresh image
         * storage; retained fds keep the retired allocation alive. */
        freeBuffers(impl, port);
        if ((res = allocBuffers(impl, port, port->streamConfig.bufferCount)) < 0)
            return res;
        spa_log_info(impl->log, "fresh image allocation after graph buffer retirement");
    }''')
p.write_text(s)
(R/'libcamera-fresh-allocation-delta.patch').write_text(''.join(difflib.unified_diff((base/p.name).read_text().splitlines(True),s.splitlines(True),fromfile='a/spa/plugins/libcamera/libcamera-source.cpp',tofile='b/spa/plugins/libcamera/libcamera-source.cpp')))
original=SDK/'work/pipewire262/pipewire-1.6.9/spa/plugins/libcamera/libcamera-source.cpp'
(R/'libcamera-fresh-allocation-candidate.patch').write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True),s.splitlines(True),fromfile='a/spa/plugins/libcamera/libcamera-source.cpp',tofile='b/spa/plugins/libcamera/libcamera-source.cpp')))
prefix='/work/pipewire265-fresh-allocation'
common=['g++','-std=c++20','-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-missing-field-initializers','-I'+prefix+'/source','-I/work/pipewire262/sdk/usr/include/spa-0.2','-I/candidate238-r14/usr/include/libcamera']
q=subprocess.run(['chroot',str(SDK),*common,'-c',prefix+'/source/libcamera-source.cpp','-o',prefix+'/libcamera-source.cpp.o'],capture_output=True);(P/'fresh-allocation-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()[-2000:]
objects=[prefix+'/libcamera-source.cpp.o']+['/'+str(p.relative_to(SDK)) for p in sorted((SDK/'work/pipewire263-automatic').glob('*.o')) if p.name!='libcamera-source.cpp.o']
q=subprocess.run(['chroot',str(SDK),'g++','-shared',*objects,'-L/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-pthread','-o',prefix+'/libspa-libcamera.so'],capture_output=True);(P/'fresh-allocation-link-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
shutil.copyfile(W/'libspa-libcamera.so',P/'libspa-libcamera-fresh-allocation.so')
report=dict(stage=265,compiled=True,source_sha256=hashlib.sha256(s.encode()).hexdigest(),spa_sha256=hashlib.sha256((P/'libspa-libcamera-fresh-allocation.so').read_bytes()).hexdigest(),core_and_gstreamer_changes_required=False,no_pixel_copy_added=True,busy_counters_never_reset=True,system_not_deployed=True)
(R/'fresh-allocation-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

