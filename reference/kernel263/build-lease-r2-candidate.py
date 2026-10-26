"""Keep the actual negotiated buffer pointers even when another port owns them."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel263');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-broadcast';p=W/'pipewire-1.6.9/src/pipewire/impl-port.c';s=p.read_text();assert 'broadcast_n_buffers' not in s
(P/'lease-core-r1-source-private.c').write_text(s)
s=s.replace('uint64_t broadcast_outstanding;', 'uint64_t broadcast_outstanding;\n\t\tstruct spa_buffer *broadcast_buffers[64];\n\t\tuint32_t broadcast_n_buffers;')
s=s.replace('id >= port->buffers.n_buffers','id >= impl->rt.broadcast_n_buffers').replace('port->buffers.buffers[id]','impl->rt.broadcast_buffers[id]').replace('buffer_id >= this->buffers.n_buffers','buffer_id >= impl->rt.broadcast_n_buffers')
needle='static int tee_process_reliable(void *object)'
helper='''static int tee_use_buffers(void *object, enum spa_direction direction,
		uint32_t port_id, uint32_t flags, struct spa_buffer **buffers,
		uint32_t n_buffers)
{
	struct impl *impl = object;
	if (!impl->reliable_broadcast || direction != SPA_DIRECTION_INPUT || port_id != 0)
		return -ENOTSUP;
	if (n_buffers > SPA_N_ELEMENTS(impl->rt.broadcast_buffers))
		return -ENOSPC;
	broadcast_reset(impl);
	impl->rt.broadcast_n_buffers = n_buffers;
	for (uint32_t i = 0; i < n_buffers; i++)
		impl->rt.broadcast_buffers[i] = buffers[i];
	return 0;
}

'''
assert s.count(needle)==1;s=s.replace(needle,helper+needle)
needle='''static const struct spa_node_methods schedule_tee_node_reliable = {
	SPA_VERSION_NODE_METHODS,'''
assert s.count(needle)==1;s=s.replace(needle,needle+'\n\t.port_use_buffers = tee_use_buffers,')
p.write_text(s)
orig=(SDK/'work/pipewire262/pipewire-1.6.9/src/pipewire/impl-port.c').read_text()
(R/'core-broadcast-lease-r2-candidate.patch').write_text(''.join(difflib.unified_diff(orig.splitlines(True),s.splitlines(True),fromfile='a/src/pipewire/impl-port.c',tofile='b/src/pipewire/impl-port.c')))
q=subprocess.run(['chroot',str(SDK),'ninja','-C','/work/pipewire263-broadcast/build','-j2','src/pipewire/libpipewire-0.3.so.0.1609.0'],capture_output=True)
(P/'lease-core-r2-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-2000:]
shutil.copyfile(W/'build/src/pipewire/libpipewire-0.3.so.0.1609.0',P/'libpipewire-lease-r2-candidate.so')
report=dict(compiled=True,core_sha256=hashlib.sha256((P/'libpipewire-lease-r2-candidate.so').read_bytes()).hexdigest(),spa_sha256=hashlib.sha256((P/'libspa-libcamera-lease-candidate.so').read_bytes()).hexdigest(),no_system_deployment=True)
(R/'lease-r2-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
