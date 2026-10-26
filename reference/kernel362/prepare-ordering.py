"""Keep the common pipeline's documented submission order across nested IPC."""
from pathlib import Path
import difflib,hashlib,json
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
name='src/libcamera/pipeline_handler.cpp';p=tree/name;before=p.read_text();s=before
a='#include <chrono>\n';assert s.count(a)==1;s=s.replace(a,a+'#include <set>\n')
a='''void PipelineHandler::doQueueRequests(Camera *camera)
{
	Camera::Private *data = camera->_d();'''
b='''void PipelineHandler::doQueueRequests(Camera *camera)
{
	/* Synchronous IPA IPC may dispatch another prepared request while
	 * queueRequestDevice() is still processing the previous one. Defer
	 * that request to this outer drain to preserve hardware queue order.
	 * CameraManager serializes these calls; keep the recursion guard per
	 * camera so another camera can still make progress in the nested loop.
	 */
	static thread_local std::set<Camera *> queueingCameras;
	if (!queueingCameras.insert(camera).second)
		return;
	struct QueueGuard {
		std::set<Camera *> &cameras;
		Camera *camera;
		~QueueGuard() { cameras.erase(camera); }
	} guard{ queueingCameras, camera };

	Camera::Private *data = camera->_d();'''
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
(HERE/'pipeline-request-order.patch').write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),s.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name)))
(HERE/'pipeline-handler-after.cpp').write_text(s)
state=json.loads((HERE/'source-state.json').read_text());state['common_ordering_file']=name;state['common_ordering_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();state['class_layout_unchanged']=True
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Prepared common per-camera ordered request drain, class layout unchanged.')
