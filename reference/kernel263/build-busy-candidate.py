"""Build a common SPA libcamera ownership candidate; never install it here."""
from pathlib import Path
import concurrent.futures,difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel263')
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-busy'
assert not W.exists();W.mkdir()
base=SDK/'work/pipewire262/pipewire-1.6.9/spa/plugins/libcamera'
source=W/'source';shutil.copytree(base,source)
p=source/'libcamera-source.cpp';original=p.read_text();s=original
def change(a,b):
 global s
 assert s.count(a)==1,a[:100]
 s=s.replace(a,b)
change('#define BUFFER_FLAG_OUTSTANDING\t(1<<0)', '#define BUFFER_FLAG_OUTSTANDING\t(1<<0)\n#define BUFFER_FLAG_PENDING_RECYCLE (1<<1)')
change('struct spa_meta_header *h;','struct spa_meta_header *h;\n\tstruct spa_meta_busy *busy;')
change('struct spa_source source = {};','struct spa_source source = { .fd = -1 };\n\tstruct spa_source recycle_source = { .fd = -1 };\n\tbool recycle_timer_armed = false;\n\tuint64_t busy_deferrals = 0, deferred_requeues = 0;')
change('''				if (self->source.loop)
					spa_loop_remove_source(self->data_loop, &self->source);''','''				if (self->source.loop)
					spa_loop_remove_source(self->data_loop, &self->source);
				if (self->recycle_source.loop)
					spa_loop_remove_source(self->data_loop, &self->recycle_source);
				self->recycle_timer_armed = false;''')
change('''		if (source.fd >= 0)
			spa_system_close(system, std::exchange(source.fd, -1));''','''		if (source.fd >= 0)
			spa_system_close(system, std::exchange(source.fd, -1));
		if (recycle_source.fd >= 0)
			spa_system_close(system, std::exchange(recycle_source.fd, -1));
		spa_log_info(log, "busy-ownership deferrals:%" PRIu64 " requeues:%" PRIu64,
			busy_deferrals, deferred_requeues);''')
start=s.index('int spa_libcamera_buffer_recycle(');end=s.index('\nvoid freeBuffers(',start)
s=s[:start]+'''
int arm_recycle_timer(struct impl *impl)
{
	if (impl->recycle_timer_armed)
		return 0;
	struct itimerspec timeout = {};
	timeout.it_value.tv_nsec = 5 * SPA_NSEC_PER_MSEC;
	int res = spa_system_timerfd_settime(impl->system,
		impl->recycle_source.fd, 0, &timeout, nullptr);
	if (res >= 0)
		impl->recycle_timer_armed = true;
	return res;
}

int spa_libcamera_buffer_recycle(struct impl *impl, struct port *port, uint32_t buffer_id)
{
	if (buffer_id >= port->n_buffers || buffer_id >= impl->requestPool.size())
		return -EINVAL;
	struct buffer *b = &port->buffers[buffer_id];
	if (!SPA_FLAG_IS_SET(b->flags, BUFFER_FLAG_OUTSTANDING))
		return 0;

	/* The graph can return its IO slot while an asynchronous consumer still
	 * owns the memory. Never hand that memory back to the camera yet. */
	if (impl->active && b->busy && SPA_ATOMIC_LOAD(b->busy->count) > 0) {
		SPA_FLAG_SET(b->flags, BUFFER_FLAG_PENDING_RECYCLE);
		impl->busy_deferrals++;
		return arm_recycle_timer(impl);
	}
	bool deferred = SPA_FLAG_IS_SET(b->flags, BUFFER_FLAG_PENDING_RECYCLE);
	if (impl->active) {
		Request *request = impl->requestPool[buffer_id].get();
		request->controls().merge(impl->ctrls);
		impl->ctrls.clear();
		int res = impl->camera->queueRequest(request);
		if (res < 0) {
			spa_log_warn(impl->log, "can't queue buffer %u: %s", buffer_id, spa_strerror(res));
			return res == -EACCES ? -EBUSY : res;
		}
		if (deferred)
			impl->deferred_requeues++;
	}
	SPA_FLAG_CLEAR(b->flags, BUFFER_FLAG_OUTSTANDING | BUFFER_FLAG_PENDING_RECYCLE);
	return 0;
}

void libcamera_recycle_timer(struct spa_source *source)
{
	auto *impl = static_cast<struct impl *>(source->data);
	uint64_t expirations;
	if (spa_system_timerfd_read(impl->system, source->fd, &expirations) < 0)
		return;
	impl->recycle_timer_armed = false;
	if (!impl->active)
		return;
	struct port *port = &impl->out_ports[0];
	for (uint32_t i = 0; i < port->n_buffers; i++) {
		if (!SPA_FLAG_IS_SET(port->buffers[i].flags, BUFFER_FLAG_PENDING_RECYCLE))
			continue;
		int res = spa_libcamera_buffer_recycle(impl, port, i);
		if (res < 0) {
			spa_log_error(impl->log, "deferred recycle failed: %s", spa_strerror(res));
			spa_node_call_ready(&impl->callbacks, res);
			return;
		}
	}
}
''' +s[end:]
change('''		b->h = (struct spa_meta_header*)spa_buffer_find_meta_data(buffers[i], SPA_META_Header, sizeof(*b->h));''','''		b->h = (struct spa_meta_header*)spa_buffer_find_meta_data(buffers[i], SPA_META_Header, sizeof(*b->h));
		b->busy = (struct spa_meta_busy*)spa_buffer_find_meta_data(buffers[i], SPA_META_Busy, sizeof(*b->busy));''')
needle='''				SPA_PARAM_META_type, SPA_POD_Id(SPA_META_VideoTransform),
				SPA_PARAM_META_size, SPA_POD_Int(sizeof(struct spa_meta_videotransform)));
			break;
		default:'''
change(needle,'''\t\t\t\tSPA_PARAM_META_type, SPA_POD_Id(SPA_META_VideoTransform),
				SPA_PARAM_META_size, SPA_POD_Int(sizeof(struct spa_meta_videotransform)));
			break;
		case 2:
			param = (struct spa_pod*)spa_pod_builder_add_object(&b,
				SPA_TYPE_OBJECT_ParamMeta, id,
				SPA_PARAM_META_type, SPA_POD_Id(SPA_META_Busy),
				SPA_PARAM_META_size, SPA_POD_Int(sizeof(struct spa_meta_busy)));
			break;
		default:''')
change('''	impl->source.rmask = 0;

	for (auto& req : impl->requestPool) {''','''	impl->source.rmask = 0;

	res = spa_system_timerfd_create(impl->system, CLOCK_MONOTONIC,
		SPA_FD_CLOEXEC | SPA_FD_NONBLOCK);
	if (res < 0)
		goto err_stop;
	impl->recycle_source.fd = res;
	impl->recycle_source.func = libcamera_recycle_timer;
	impl->recycle_source.data = impl;
	impl->recycle_source.mask = SPA_IO_IN | SPA_IO_ERR;
	impl->recycle_source.rmask = 0;
	impl->recycle_timer_armed = false;

	for (auto& req : impl->requestPool) {''')
change('''		req->reuse(libcamera::Request::ReuseFlag::ReuseBuffers);

		if ((res = impl->camera->queueRequest(req.get())) < 0)''','''		req->reuse(libcamera::Request::ReuseFlag::ReuseBuffers);
		struct buffer *b = &port->buffers[req->cookie()];
		if (b->busy && SPA_ATOMIC_LOAD(b->busy->count) > 0) {
			SPA_FLAG_SET(b->flags, BUFFER_FLAG_OUTSTANDING | BUFFER_FLAG_PENDING_RECYCLE);
			continue;
		}
		SPA_FLAG_CLEAR(b->flags, BUFFER_FLAG_OUTSTANDING | BUFFER_FLAG_PENDING_RECYCLE);
		if ((res = impl->camera->queueRequest(req.get())) < 0)''')
change('''			return spa_loop_add_source(impl->data_loop, &impl->source);''','''			int res = spa_loop_add_source(impl->data_loop, &impl->source);
			if (res < 0)
				return res;
			res = spa_loop_add_source(impl->data_loop, &impl->recycle_source);
			if (res < 0)
				return res;
			for (uint32_t i = 0; i < impl->out_ports[0].n_buffers; i++) {
				if (SPA_FLAG_IS_SET(impl->out_ports[0].buffers[i].flags, BUFFER_FLAG_PENDING_RECYCLE))
					return arm_recycle_timer(impl);
			}
			return 0;''')
p.write_text(s)
(R/'libcamera-busy-ownership-candidate.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/spa/plugins/libcamera/libcamera-source.cpp',tofile='b/spa/plugins/libcamera/libcamera-source.cpp')))
def inside(args):return subprocess.run(['chroot',str(SDK),*args],capture_output=True)
common=['-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-I/work/pipewire263-busy/source','-I/work/pipewire262/sdk/usr/include/spa-0.2','-I/candidate238-r14/usr/include/libcamera']
def compile_one(name):
 obj=W/(name+'.o');compiler='cc' if name.endswith('.c') else 'g++'
 args=[compiler,*common,*([] if compiler=='cc' else ['-std=c++20']),'-c','/'+str((source/name).relative_to(SDK)),'-o','/'+str(obj.relative_to(SDK))]
 q=inside(args);(P/(name+'-build-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,name
 return '/'+str(obj.relative_to(SDK))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:objects=list(pool.map(compile_one,['libcamera.c','libcamera-manager.cpp','libcamera-device.cpp','libcamera-source.cpp']))
binary=W/'libspa-libcamera.so'
q=inside(['g++','-shared',*objects,'-L/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-pthread','-o','/'+str(binary.relative_to(SDK))]);(P/'spa-link-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
shutil.copyfile(binary,P/'libspa-libcamera-busy-candidate.so')
report=dict(stage=263,compiled=True,source_sha256=hashlib.sha256(s.encode()).hexdigest(),plugin_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),candidate_only=True,installed_system_not_modified=True)
(R/'busy-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
