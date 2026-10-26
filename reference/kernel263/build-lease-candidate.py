"""Track camera broadcast ownership per link, including disconnected clients."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel263');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-broadcast';base=SDK/'work/pipewire262/pipewire-1.6.9'
p=W/'pipewire-1.6.9/src/pipewire/impl-port.c';s=p.read_text();assert 'struct broadcast_owner' not in s
(P/'broadcast-core-r1-source-private.c').write_text(s)
def change(a,b):
 global s
 assert s.count(a)==1,a[:80];s=s.replace(a,b)
change('struct impl {','''struct broadcast_owner {
	struct spa_list link;
	struct pw_impl_port_mix *mix;
	uint64_t pending;
};

struct impl {''')
change('struct spa_list mix_list;\n\t} rt;', 'struct spa_list mix_list;\n\t\tstruct spa_list broadcast_owners;\n\t\tuint64_t broadcast_outstanding;\n\t} rt;')
helper='''static struct broadcast_owner *broadcast_find_owner(struct impl *impl,
		struct pw_impl_port_mix *mix)
{
	struct broadcast_owner *owner;
	spa_list_for_each(owner, &impl->rt.broadcast_owners, link)
		if (owner->mix == mix)
			return owner;
	return NULL;
}

static void broadcast_reset(struct impl *impl)
{
	struct broadcast_owner *owner;
	impl->rt.broadcast_outstanding = 0;
	spa_list_for_each(owner, &impl->rt.broadcast_owners, link)
		owner->pending = 0;
}

static int broadcast_release_idle(struct impl *impl)
{
	struct pw_impl_port *port = &impl->this;
	struct broadcast_owner *owner;
	uint64_t pending = 0, ready;
	spa_list_for_each(owner, &impl->rt.broadcast_owners, link)
		pending |= owner->pending;
	ready = impl->rt.broadcast_outstanding & ~pending;
	for (uint32_t id = 0; id < 64; id++) {
		uint64_t bit = UINT64_C(1) << id;
		if (!(ready & bit))
			continue;
		impl->rt.broadcast_outstanding &= ~bit;
		if (port->destroying || !port->node || id >= port->buffers.n_buffers)
			continue;
		/* No live link owns this buffer now. A vanished client can leave its
		 * shared Busy counter elevated; clearing it is safe only here, after
		 * every remaining client returned its own lease. */
		struct spa_meta_busy *busy = spa_buffer_find_meta_data(
			port->buffers.buffers[id], SPA_META_Busy, sizeof(*busy));
		if (busy)
			SPA_ATOMIC_STORE(busy->count, 0);
		int res = spa_node_port_reuse_buffer(port->node->node, port->port_id, id);
		if (res < 0)
			return res;
	}
	return 0;
}

'''
change('static int\ndo_add_mix(',helper+'static int\ndo_add_mix(')
change('''	if (!mix->rt.active) {
		spa_list_append(&impl->rt.mix_list, &mix->rt.link);''','''	if (!mix->rt.active) {
		if (impl->reliable_broadcast) {
			struct broadcast_owner *owner = calloc(1, sizeof(*owner));
			if (!owner)
				return -ENOMEM;
			owner->mix = mix;
			spa_list_append(&impl->rt.broadcast_owners, &owner->link);
		}
		spa_list_append(&impl->rt.mix_list, &mix->rt.link);''')
change('''	struct pw_impl_port *this = mix->p;
	pw_log_trace("%p: remove mix %p", this, mix);''','''	struct pw_impl_port *this = mix->p;
	struct impl *impl = SPA_CONTAINER_OF(this, struct impl, this);
	pw_log_trace("%p: remove mix %p", this, mix);''')
change('''		mix->rt.active = false;
	}
	return 0;
}

static int port_set_io''','''		mix->rt.active = false;
		struct broadcast_owner *owner = broadcast_find_owner(impl, mix);
		if (owner) {
			spa_list_remove(&owner->link);
			free(owner);
			return broadcast_release_idle(impl);
		}
	}
	return 0;
}

static int port_set_io''')
start=s.index('/* Opt-in camera fanout:');end=s.index('static int tee_process_reliable(void *object)',start)
s=s[:start]+'''/* Reliable camera fanout tracks each link's lease until that exact client
 * returns the buffer or the link is removed. Never infer ownership from the
 * first ready consumer, and never discard another client's outstanding slot. */
static int tee_process_reliable_broadcast(void *object)
{
	struct impl *impl = object;
	struct pw_impl_port *this = &impl->this;
	struct pw_impl_port_mix *mix;
	struct spa_io_buffers *io = &this->rt.io;
	uint32_t cycle = this->node->rt.position->clock.cycle & 1;
	uint32_t buffer_id;
	bool delivered = false;
	int res;

	spa_list_for_each(mix, &impl->rt.mix_list, rt.link) {
		struct broadcast_owner *owner = broadcast_find_owner(impl, mix);
		if (!owner)
			return -EIO;
		for (uint32_t c = 0; c < 2; c++) {
			struct spa_io_buffers *mio = mix->io[c];
			if (mio->status == SPA_STATUS_HAVE_DATA || mio->buffer_id == SPA_ID_INVALID)
				continue;
			if (mio->buffer_id < 64)
				owner->pending &= ~(UINT64_C(1) << mio->buffer_id);
			mio->buffer_id = SPA_ID_INVALID;
		}
	}
	if ((res = broadcast_release_idle(impl)) < 0)
		return res;
	if (io->status != SPA_STATUS_HAVE_DATA)
		return SPA_STATUS_HAVE_DATA | SPA_STATUS_NEED_DATA;
	spa_list_for_each(mix, &impl->rt.mix_list, rt.link) {
		if (mix->io[cycle]->status == SPA_STATUS_HAVE_DATA)
			return SPA_STATUS_HAVE_DATA | SPA_STATUS_NEED_DATA;
	}
	buffer_id = io->buffer_id;
	if (buffer_id >= 64 || buffer_id >= this->buffers.n_buffers)
		return -EINVAL;
	spa_list_for_each(mix, &impl->rt.mix_list, rt.link) {
		struct spa_io_buffers *mio = mix->io[cycle];
		struct broadcast_owner *owner = broadcast_find_owner(impl, mix);
		owner->pending |= UINT64_C(1) << buffer_id;
		impl->rt.broadcast_outstanding |= UINT64_C(1) << buffer_id;
		mio->buffer_id = buffer_id;
		mio->status = SPA_STATUS_HAVE_DATA;
		delivered = true;
	}
	io->buffer_id = delivered ? SPA_ID_INVALID : buffer_id;
	io->status = SPA_STATUS_NEED_DATA;
	return SPA_STATUS_HAVE_DATA | SPA_STATUS_NEED_DATA;
}

'''+s[end:]
change('spa_list_init(&impl->rt.mix_list);','spa_list_init(&impl->rt.mix_list);\n\tspa_list_init(&impl->rt.broadcast_owners);')
change('''	if (id == SPA_PARAM_Format) {
		/* setting the format always destroys the negotiated buffers */''','''	if (id == SPA_PARAM_Format) {
		struct impl *impl = SPA_CONTAINER_OF(port, struct impl, this);
		broadcast_reset(impl);
		/* setting the format always destroys the negotiated buffers */''')
p.write_text(s)
orig=(base/'src/pipewire/impl-port.c').read_text()
(R/'core-broadcast-lease-candidate.patch').write_text(''.join(difflib.unified_diff(orig.splitlines(True),s.splitlines(True),fromfile='a/src/pipewire/impl-port.c',tofile='b/src/pipewire/impl-port.c')))
def inside(args,log):
 q=subprocess.run(['chroot',str(SDK),*args],capture_output=True);(P/log).write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-3000:]
prefix='/work/pipewire263-broadcast'
inside(['ninja','-C',prefix+'/build','-j2','src/pipewire/libpipewire-0.3.so.0.1609.0'],'lease-core-build-private.log')
shutil.copyfile(W/'build/src/pipewire/libpipewire-0.3.so.0.1609.0',P/'libpipewire-lease-candidate.so')
q=W/'spa/libcamera-source.cpp';sp=q.read_text();(P/'broadcast-spa-r1-source-private.cpp').write_text(sp)
needle='''	struct port *port = &impl->out_ports[0];
	for (uint32_t i = 0; i < port->n_buffers; i++) {
		if (!SPA_FLAG_IS_SET(port->buffers[i].flags, BUFFER_FLAG_PENDING_RECYCLE))'''
assert sp.count(needle)==1
sp=sp.replace(needle,needle.replace('\n\tfor (','\n\tbool all_outstanding = port->n_buffers > 0;\n\tfor (').replace('\n\t\tif (!SPA_FLAG_IS_SET', '\n\t\tall_outstanding &= SPA_FLAG_IS_SET(port->buffers[i].flags, BUFFER_FLAG_OUTSTANDING);\n\t\tif (!SPA_FLAG_IS_SET'))
needle='''			return;
		}
	}
}

void freeBuffers'''
assert sp.count(needle)==1
sp=sp.replace(needle,'''\t\t\treturn;
		}
	}
	/* With the whole pool held, no camera completion can run the graph to
	 * collect already-returned input IO slots. Poll only that exhausted case. */
	if (all_outstanding && spa_list_is_empty(&port->queue)) {
		spa_node_call_ready(&impl->callbacks, SPA_STATUS_NEED_DATA);
		arm_recycle_timer(impl);
	}
}

void freeBuffers''')
needle='''	spa_node_call_ready(&impl->callbacks, SPA_STATUS_HAVE_DATA);
}

void libcamera_on_fd_events'''
assert sp.count(needle)==1
sp=sp.replace(needle,'''\tbool all_outstanding = port->n_buffers > 0;
	for (uint32_t i = 0; i < port->n_buffers; i++)
		all_outstanding &= SPA_FLAG_IS_SET(port->buffers[i].flags, BUFFER_FLAG_OUTSTANDING);
	if (all_outstanding)
		arm_recycle_timer(impl);
	spa_node_call_ready(&impl->callbacks, SPA_STATUS_HAVE_DATA);
}

void libcamera_on_fd_events''')
q.write_text(sp)
common=['g++','-std=c++20','-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-missing-field-initializers','-I'+prefix+'/spa','-I/work/pipewire262/sdk/usr/include/spa-0.2','-I/candidate238-r14/usr/include/libcamera']
inside([*common,'-c',prefix+'/spa/libcamera-source.cpp','-o',prefix+'/libcamera-source.cpp.o'],'lease-spa-build-private.log')
objects=[prefix+'/libcamera-source.cpp.o']+['/'+str(p.relative_to(SDK)) for p in sorted((SDK/'work/pipewire263-automatic').glob('*.o')) if p.name!='libcamera-source.cpp.o']
inside(['g++','-shared',*objects,'-L/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-pthread','-o',prefix+'/libspa-libcamera.so'],'lease-spa-link-private.log')
shutil.copyfile(W/'libspa-libcamera.so',P/'libspa-libcamera-lease-candidate.so')
orig=(base/'spa/plugins/libcamera/libcamera-source.cpp').read_text()
(R/'libcamera-broadcast-lease-candidate.patch').write_text(''.join(difflib.unified_diff(orig.splitlines(True),sp.splitlines(True),fromfile='a/spa/plugins/libcamera/libcamera-source.cpp',tofile='b/spa/plugins/libcamera/libcamera-source.cpp')))
report=dict(stage=263,compiled=True,core_sha256=hashlib.sha256((P/'libpipewire-lease-candidate.so').read_bytes()).hexdigest(),spa_sha256=hashlib.sha256((P/'libspa-libcamera-lease-candidate.so').read_bytes()).hexdigest(),no_system_deployment=True)
(R/'lease-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
