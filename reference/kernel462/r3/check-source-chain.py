"""Recompute the reachable late-FD chain from cached exact source bodies."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('chain462r3_storage449',HERE.parents[1]/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
SHARED=storage.mount.mounted_build()
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel462/r3')
sha=lambda text:hashlib.sha256(text.encode()).hexdigest()
read=lambda name:(PRIVATE/'source'/name).read_text()
def function(text,signature):
    start=text.index(signature);end=text.index('{',start)+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end],text[:start].count('\n')+1,text[:end].count('\n')+1
paths={
    'camss':'drivers/media/platform/qcom/camss/camss.c',
    'async':'drivers/media/v4l2-core/v4l2-async.c',
    'device':'drivers/media/v4l2-core/v4l2-device.c',
    'node':'drivers/media/v4l2-core/v4l2-dev.c',
    'subdev':'drivers/media/v4l2-core/v4l2-subdev.c',
    'fh':'drivers/media/v4l2-core/v4l2-fh.c',
    'driver':'drivers/base/dd.c'}
signatures={
    'camss':['static int camss_subdev_notifier_complete('],
    'async':['void v4l2_async_unregister_subdev(', 'static void v4l2_async_unbind_subdev_one('],
    'device':['void v4l2_device_unregister_subdev(', 'static void v4l2_subdev_release(',
              'static void v4l2_device_release_subdev_node(', 'int __v4l2_device_register_subdev_nodes('],
    'node':['static int v4l2_open(', 'static int v4l2_release(', 'void video_unregister_device('],
    'subdev':['static int subdev_open(', 'static int subdev_close(', 'static __poll_t subdev_poll(',
              'static long subdev_do_ioctl_lock(', 'void v4l2_subdev_cleanup(',
              '__v4l2_subdev_state_alloc(struct v4l2_subdev *sd,'],
    'fh':['void v4l2_fh_init(', 'void v4l2_fh_exit('],
    'driver':['static void device_unbind_cleanup(', 'static void __device_release_driver(']}
rows=[];bodies={}
for key,names in signatures.items():
    source=read(paths[key]);original=(PRIVATE/'original363'/paths[key]).read_text()
    for signature in names:
        body,start,end=function(source,signature)
        old=function(original,signature)[0]
        rows.append(dict(path=paths[key],signature=signature,line=start,end_line=end,
                         function_sha256=sha(body),equal_image363_function=old==body))
        bodies[signature]=body
assert all(row['equal_image363_function'] for row in rows)
config=(PRIVATE.parent.parent/'kernel457/config363-private').read_text()
assert 'CONFIG_VIDEO_V4L2_SUBDEV_API=y\n' in config
assert 'v4l2_device_register_subdev_nodes(' in bodies['static int camss_subdev_notifier_complete(']
assert 'v4l2_device_unregister_subdev(' in bodies['static void v4l2_async_unbind_subdev_one(']
unreg=bodies['void v4l2_device_unregister_subdev(']
assert 'video_unregister_device(sd->devnode)' in unreg and 'v4l2_subdev_release(sd)' in unreg
assert 'video_get(vdev)' in bodies['static int v4l2_open('] and 'video_put(vdev)' in bodies['static int v4l2_release(']
assert 'sd->internal_ops' in bodies['static int subdev_close(']
assert 'sd->flags' in bodies['static __poll_t subdev_poll(']
assert 'fh->ctrl_handler = vdev->ctrl_handler' in bodies['void v4l2_fh_init(']
assert 'video_is_registered(vdev)' in bodies['static long subdev_do_ioctl_lock(']
assert 'devres_release_all(dev)' in bodies['static void device_unbind_cleanup(']
unbind=bodies['static void __device_release_driver(']
assert unbind.index('device_remove(dev)')<unbind.index('device_unbind_cleanup(dev)')
r2=(PRIVATE/'r2-imx471-private.c').read_text();r3=(PRIVATE/'candidate/drivers/media/i2c/imx471.c').read_text()
r2ops=r2[r2.index('static const struct v4l2_subdev_internal_ops imx471_internal_ops'):]
r2ops=r2ops[:r2ops.index('\n};')+3]
assert '.init_state' in r2ops and '.release' not in r2ops and '.registered' not in r2ops
assert 'V4L2_SUBDEV_FL_HAS_DEVNODE' in r2 and 'sensor = devm_kzalloc(' in r2
old_remove=function(r2,'static void imx471_remove(')[0]
assert all(name in old_remove for name in ['v4l2_async_unregister_subdev','v4l2_subdev_cleanup','media_entity_cleanup','v4l2_ctrl_handler_free'])
assert 'devm_kzalloc' not in r3 and '.registered = imx471_registered' in r3 and '.release = imx471_release' in r3
assert 'ctrl_hdlr->lock = &sensor->lock' in r3 and 'sensor->sd.state_lock = &sensor->lock' in r3
guards=[]
for signature,operation in [('static int imx471_set_ctrl(', 'pm_runtime_get_if_in_use('),
                            ('static int imx471_set_pad_format(', 'imx471_find_mode('),
                            ('static int imx471_enable_stream(', 'pm_runtime_resume_and_get('),
                            ('static int imx471_disable_stream(', 'cci_write(')]:
    body,line,end=function(r3,signature)
    assert body.index('if (sensor->removing)')<body.index(operation)
    guards.append(dict(signature=signature,line=line,end_line=end,function_sha256=sha(body),guard_before=operation))
detach=function(r3,'static void imx471_detach(')[0]
assert detach.index('sensor->removing = true')<detach.index('v4l2_async_unregister_subdev(')<detach.index('pm_runtime_disable(')<detach.index('kref_put(')
assert 'v4l2_subdev_cleanup' not in detach and 'v4l2_ctrl_handler_free' not in detach
assert 'No control/state lock is held' in r3
core=read(paths['device'])
fixed=core.replace('\tif (sd->internal_ops && sd->internal_ops->release)\n\t\tsd->internal_ops->release(sd);\n\tsd->devnode = NULL;',
                   '\tsd->devnode = NULL;\n\tif (sd->internal_ops && sd->internal_ops->release)\n\t\tsd->internal_ops->release(sd);')
record456=json.loads((HERE.parents[1]/'kernel456/source-validation.json').read_text())
assert sha(fixed)==record456['actual_core_sha256']
report=dict(stage=462,revision='r3',passed=True,functions=rows,all_chain_functions_equal_image363=True,
    video_v4l2_subdev_api_enabled=True,camss_creates_writable_subdev_nodes=True,
    imx471_has_devnode_and_r2_lacks_registered_release_refs=True,
    late_close_and_final_node_release_reach_sensor_after_remove=True,
    r2_ctrl_state_entity_cleanup_and_devres_can_precede_final_fd_close=True,
    module_and_video_device_refs_do_not_own_sensor_allocation=True,
    core0064_only_orders_callback_and_devnode_store_not_sensor_driver_lifetime=True,
    core0064_exact_source_sha256=sha(fixed),r3_guard_source=guards,
    r3_single_lock_for_controls_active_and_fh_state=True,
    r3_detach_does_not_destroy_control_state_entity=True,
    already_open_stopped_fds_can_be_modeled_across_controlled_unbind=True,
    all_concurrent_open_stream_graph_unbind_interleavings_proven=False,
    current_phone_node_or_fd_state_queried=False,phone_or_sdk_accessed=False)
(HERE/'source-chain-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,chain_functions=len(rows),r2_real_reachable_gap=True,guards=guards)),flush=True)
