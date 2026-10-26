"""Build isolated opt-in reliable fanout and the matching common camera source."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel263');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-broadcast';assert not W.exists();W.mkdir()
base=SDK/'work/pipewire262/pipewire-1.6.9';source=W/'pipewire-1.6.9';shutil.copytree(base,source)
p=source/'src/pipewire/impl-port.c';original=p.read_text();s=original
def change(a,b):
 global s
 assert s.count(a)==1,a[:80];s=s.replace(a,b)
change('unsigned int cache_params:1;', 'unsigned int cache_params:1;\n\tbool reliable_broadcast;')
needle='static int tee_process_reliable(void *object)'
fanout='''/* Opt-in camera fanout: wait for every graph recipient to accept its IO
 * slot before publishing another frame. Application-held memory is protected
 * separately by the producer's shared Busy metadata. */
static int tee_process_reliable_broadcast(void *object)
{
	struct impl *impl = object;
	struct pw_impl_port *this = &impl->this;
	struct pw_impl_port_mix *mix;
	struct spa_io_buffers *io = &this->rt.io;
	uint32_t cycle = this->node->rt.position->clock.cycle & 1;
	uint32_t buffer_id;
	bool delivered = false;

	if (io->status != SPA_STATUS_HAVE_DATA)
		return SPA_STATUS_HAVE_DATA | SPA_STATUS_NEED_DATA;
	spa_list_for_each(mix, &impl->rt.mix_list, rt.link) {
		if (mix->io[cycle]->status == SPA_STATUS_HAVE_DATA)
			return SPA_STATUS_HAVE_DATA | SPA_STATUS_NEED_DATA;
	}
	buffer_id = io->buffer_id;
	spa_list_for_each(mix, &impl->rt.mix_list, rt.link) {
		struct spa_io_buffers *mio = mix->io[cycle];
		if (mio->buffer_id != SPA_ID_INVALID) {
			int res = spa_node_port_reuse_buffer(this->node->node,
				this->port_id, mio->buffer_id);
			if (res < 0)
				return res;
		}
		mio->buffer_id = buffer_id;
		mio->status = SPA_STATUS_HAVE_DATA;
		delivered = true;
	}
	io->buffer_id = delivered ? SPA_ID_INVALID : buffer_id;
	io->status = SPA_STATUS_NEED_DATA;
	return SPA_STATUS_HAVE_DATA | SPA_STATUS_NEED_DATA;
}

'''
change(needle,fanout+needle)
change('''static int tee_process_reliable(void *object)
{
	struct impl *impl = object;''','''static int tee_process_reliable(void *object)
{
	struct impl *impl = object;
	if (impl->reliable_broadcast)
		return tee_process_reliable_broadcast(object);''')
change('''	new_bool = pw_properties_get_bool(port->properties, PW_KEY_PORT_RELIABLE, node->reliable);''','''	impl->reliable_broadcast = pw_properties_get_bool(nprops, "node.reliable.broadcast", false);
	new_bool = pw_properties_get_bool(port->properties, PW_KEY_PORT_RELIABLE, node->reliable);''')
p.write_text(s)
(R/'core-reliable-broadcast-candidate.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/src/pipewire/impl-port.c',tofile='b/src/pipewire/impl-port.c')))
def inside(args,log):
 q=subprocess.run(['chroot',str(SDK),*args],capture_output=True);(P/log).write_bytes(q.stdout+q.stderr)
 if q.returncode:print((q.stdout+q.stderr).decode(errors='replace')[-5000:]);raise RuntimeError(log)
 return q
prefix='/work/pipewire263-broadcast'
inside(['meson','setup',prefix+'/build',prefix+'/pipewire-1.6.9','--prefix=/usr','--libdir=lib','--buildtype=release','-Dauto_features=disabled','-Dsession-managers=[]','-Dexamples=disabled','-Dtests=disabled','-Dpipewire-jack=disabled','-Dpipewire-v4l2=disabled','-Ddbus=disabled','-Dflatpak=disabled','-Dspa-plugins=disabled'],'broadcast-core-configure-private.log')
inside(['ninja','-C',prefix+'/build','-j4','src/pipewire/libpipewire-0.3.so.0.1609.0'],'broadcast-core-build-private.log')
core=W/'build/src/pipewire/libpipewire-0.3.so.0.1609.0';assert core.exists();shutil.copyfile(core,P/'libpipewire-broadcast-candidate.so')
spa=W/'spa';shutil.copytree(SDK/'work/pipewire263-automatic/source',spa)
q=spa/'libcamera-source.cpp';sp=q.read_text();needle='{ "node.reliable", "true" },';assert sp.count(needle)==1;sp=sp.replace(needle,needle+'\n\t\t{ "node.reliable.broadcast", "true" },');q.write_text(sp)
common=['g++','-std=c++20','-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-missing-field-initializers','-I'+prefix+'/spa','-I/work/pipewire262/sdk/usr/include/spa-0.2','-I/candidate238-r14/usr/include/libcamera']
inside([*common,'-c',prefix+'/spa/libcamera-source.cpp','-o',prefix+'/libcamera-source.cpp.o'],'broadcast-spa-build-private.log')
objects=[prefix+'/libcamera-source.cpp.o']+['/'+str(p.relative_to(SDK)) for p in sorted((SDK/'work/pipewire263-automatic').glob('*.o')) if p.name!='libcamera-source.cpp.o']
inside(['g++','-shared',*objects,'-L/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-pthread','-o',prefix+'/libspa-libcamera.so'],'broadcast-spa-link-private.log')
shutil.copyfile(W/'libspa-libcamera.so',P/'libspa-libcamera-broadcast-candidate.so')
original=(base/'spa/plugins/libcamera/libcamera-source.cpp').read_text()
(R/'libcamera-broadcast-ownership-candidate.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),sp.splitlines(True),fromfile='a/spa/plugins/libcamera/libcamera-source.cpp',tofile='b/spa/plugins/libcamera/libcamera-source.cpp')))
report=dict(stage=263,compiled=True,core_sha256=hashlib.sha256(core.read_bytes()).hexdigest(),spa_sha256=hashlib.sha256((W/'libspa-libcamera.so').read_bytes()).hexdigest(),no_system_deployment=True)
(R/'broadcast-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
