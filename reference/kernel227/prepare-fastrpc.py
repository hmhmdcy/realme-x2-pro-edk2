"""Prepare an isolated FastRPC candidate; never modify the maintained kernel."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel227')
KERNEL = Path('/home/cy122/pmos-samurai-kernel136/kernel')
BUILD = Path('/home/cy122/x2pro-linux/fastrpc227-publication')
BASE_SHA = '41c8db5c323404dbd6230a43206ff573e0f5ad327574d3ffe94cc741ca6da347'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot():
    names = {
        '.config', 'Module.symvers', 'modules.order', 'Makefile',
        'include/config/kernel.release', 'include/config/auto.conf',
        'include/generated/autoconf.h', 'include/generated/utsrelease.h',
        'arch/arm64/boot/Image',
        'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',
        'drivers/misc/fastrpc.c', 'drivers/misc/fastrpc.o',
        'drivers/misc/fastrpc.ko', 'drivers/misc/.fastrpc.o.cmd',
        'drivers/misc/.fastrpc.ko.cmd', 'scripts/module.lds',
    }
    for args in (['ls-files', '-m', '-z'], ['ls-files', '--others', '--exclude-standard', '-z']):
        names.update(subprocess.check_output(['git', *args], cwd=KERNEL).decode().rstrip('\0').split('\0'))
    result = {n: digest((KERNEL / n).read_bytes()) for n in sorted(names) if n and (KERNEL / n).is_file()}
    result['git_status_z_sha256'] = digest(subprocess.check_output(['git', 'status', '--porcelain=v1', '-z'], cwd=KERNEL))
    result['git_diff_sha256'] = digest(subprocess.check_output(['git', 'diff', '--binary'], cwd=KERNEL))
    return result


def replace_once(source, old, new):
    assert source.count(old) == 1, old[:100]
    return source.replace(old, new, 1)


def make_patch(base, new):
    description = '''Subject: [PATCH] misc: fastrpc: initialize channels before publishing misc nodes

An early open can reach an uninitialized channel. A second misc-node
registration failure can race an already published first node.
Initialize all state before publication. Gate opens until all
registrations succeed.

Keep the initial channel reference in devres until RPMsg has destroyed its
callback endpoint. Unwind partial child populations and restore the parent
DMA masks when releasing that owner reference. Preserve the freezer wait.
Pin the module for open files and unregister RPMsg before its CB driver.
This does not implement invocation/DMA draining during DSP restart.

---
diff --git a/drivers/misc/fastrpc.c b/drivers/misc/fastrpc.c
'''
    return description + ''.join(difflib.unified_diff(
        base.splitlines(True), new.splitlines(True),
        fromfile='a/drivers/misc/fastrpc.c', tofile='b/drivers/misc/fastrpc.c'))


def candidate(base):
    source = replace_once(base, '#include <linux/slab.h>\n', '#include <linux/slab.h>\n#include <linux/smp.h>\n')
    source = replace_once(source, '\tstruct rpmsg_device *rpdev;\n',
                         '\tstruct rpmsg_device *rpdev;\n'
                         '\tstruct device *dev;\n'
                         '\tu64 *original_dma_mask;\n'
                         '\tu64 original_coherent_dma_mask;\n'
                         '\t/* Protected by lock; all misc nodes must exist before opening. */\n'
                         '\tbool ready;\n')
    start = source.index('static struct fastrpc_session_ctx *fastrpc_session_alloc(')
    end = source.index('\nstatic void fastrpc_session_free', start)
    source = source[:start] + '''static struct fastrpc_session_ctx *fastrpc_session_alloc_locked(struct fastrpc_user *fl)
{
	struct fastrpc_channel_ctx *cctx = fl->cctx;
	struct fastrpc_session_ctx *session = NULL;
	int i;

	lockdep_assert_held(&cctx->lock);
	for (i = 0; i < cctx->sesscount; i++) {
		if (!cctx->session[i].used && cctx->session[i].valid) {
			cctx->session[i].used = true;
			session = &cctx->session[i];
			/* any non-zero ID will work, session_idx + 1 is the simplest one */
			fl->client_id = i + 1;
			break;
		}
	}

	return session;
}
''' + source[end:]
    start = source.index('static int fastrpc_device_open(')
    end = source.index('\nstatic int fastrpc_dmabuf_alloc', start)
    source = source[:start] + '''static int fastrpc_device_open(struct inode *inode, struct file *filp)
{
	struct fastrpc_channel_ctx *cctx;
	struct fastrpc_device *fdevice;
	struct fastrpc_user *fl;
	unsigned long flags;
	int err;

	fdevice = miscdev_to_fdevice(filp->private_data);
	cctx = fdevice->cctx;

	fl = kzalloc_obj(*fl);
	if (!fl)
		return -ENOMEM;

	spin_lock_init(&fl->lock);
	mutex_init(&fl->mutex);
	INIT_LIST_HEAD(&fl->pending);
	INIT_LIST_HEAD(&fl->maps);
	INIT_LIST_HEAD(&fl->mmaps);
	INIT_LIST_HEAD(&fl->user);
	kref_init(&fl->refcount);
	fl->cctx = cctx;
	fl->is_secure_dev = fdevice->secure;

	/* misc_open() holds misc_mtx, so the device and owner ref are live. */
	spin_lock_irqsave(&cctx->lock, flags);
	if (!cctx->ready || !cctx->rpdev) {
		err = -ENODEV;
		goto err_unlock;
	}

	fl->sctx = fastrpc_session_alloc_locked(fl);
	if (!fl->sctx) {
		err = -EBUSY;
		goto err_unlock;
	}

	/* Released by fastrpc_user_free(), after the last user reference. */
	fastrpc_channel_ctx_get(cctx);
	list_add_tail(&fl->user, &cctx->users);
	spin_unlock_irqrestore(&cctx->lock, flags);
	filp->private_data = fl;

	return 0;

err_unlock:
	spin_unlock_irqrestore(&cctx->lock, flags);
	mutex_destroy(&fl->mutex);
	kfree(fl);
	return err;
}
''' + source[end:]
    start = source.index('static int fastrpc_rpmsg_probe(')
    end = source.index('\nstatic void fastrpc_notify_users', start)
    old_probe = source[start:end]
    # Keep the validated property/domain/SCM handling; initialize before any publication.
    prefix = old_probe[:old_probe.index('\tif (vmcount) {')]
    prefix = replace_once(prefix, '\tunsigned int vmids[FASTRPC_MAX_VMIDS];\n',
                          '\tunsigned int vmids[FASTRPC_MAX_VMIDS];\n\tunsigned long flags;\n')
    init = '''	kref_init(&data->refcount);
	atomic_set(&data->ctx_seq, 0);
	INIT_LIST_HEAD(&data->users);
	INIT_LIST_HEAD(&data->invoke_interrupted_mmaps);
	spin_lock_init(&data->lock);
	idr_init(&data->ctx_idr);
	data->domain_id = domain_id;
	data->rpdev = rpdev;
	data->dev = rdev;
	data->original_dma_mask = rdev->dma_mask;
	data->original_coherent_dma_mask = rdev->coherent_dma_mask;
	secure_dsp = !of_property_read_bool(rdev->of_node, "qcom,non-secure-domain");
	data->secure = secure_dsp;
	data->soc_data = soc_data;
	data->poll_mode_supported = soc_data->poll_mode_supported ||
		of_machine_get_match(fastrpc_poll_supported_machines);
	data->unsigned_support = domain_id == CDSP_DOMAIN_ID || domain_id == GDSP_DOMAIN_ID;

	/* RPMsg destroys the endpoint before driver core releases devres. */
	err = devm_add_action_or_reset(rdev, fastrpc_channel_ctx_release, data);
	if (err)
		return err;

'''
    middle = old_probe[old_probe.index('\tif (vmcount) {'):old_probe.index('\tsecure_dsp =')]
    middle = middle.replace('goto err_free_data;', 'return err;')
    publish = '''	rdev->dma_mask = &data->dma_mask;
	err = dma_set_mask_and_coherent(rdev, DMA_BIT_MASK(32));
	if (err)
		return err;

	/* The endpoint can receive callbacks before probe returns. */
	smp_store_release(&rdev->driver_data, data);
	err = of_platform_populate(rdev->of_node, NULL, NULL, rdev);
	if (err)
		goto err_depopulate;

'''
    register = old_probe[old_probe.index('\tswitch (domain_id) {'):old_probe.index('\tkref_init(&data->refcount);')]
    register = register.replace('\t\tdata->unsigned_support = false;\n', '').replace('\t\tdata->unsigned_support = true;\n', '')
    register = register.replace('goto err_free_data;', 'goto err_deregister_fdev;')
    suffix = '''	spin_lock_irqsave(&data->lock, flags);
	data->ready = true;
	spin_unlock_irqrestore(&data->lock, flags);
	return 0;

err_deregister_fdev:
	if (data->fdevice)
		misc_deregister(&data->fdevice->miscdev);
	if (data->secure_fdevice)
		misc_deregister(&data->secure_fdevice->miscdev);
err_depopulate:
	of_platform_depopulate(rdev);
	/* Unpublish from callback acquire readers; devm still owns the channel. */
	smp_store_release(&rdev->driver_data, NULL);
	/* The devm action retains the owner ref until endpoint callbacks drain. */
	return err;
}
'''
    release = '''/* Runs after endpoint destruction and child/device resource cleanup. */
static void fastrpc_channel_ctx_release(void *data)
{
	struct fastrpc_channel_ctx *cctx = data;
	struct device *dev = cctx->dev;

	/* Pair with callback acquire readers after endpoint destruction. */
	smp_store_release(&dev->driver_data, NULL);
	dev->dma_mask = cctx->original_dma_mask;
	dev->coherent_dma_mask = cctx->original_coherent_dma_mask;
	fastrpc_channel_ctx_put(cctx);
}

'''
    source = source[:start] + release + prefix + init + middle + publish + register + suffix + source[end:]
    source = replace_once(source, '\tcctx->rpdev = NULL;\n', '\tcctx->ready = false;\n\tcctx->rpdev = NULL;\n')
    source = replace_once(source, '\tof_platform_depopulate(&rpdev->dev);\n\n\tfastrpc_channel_ctx_put(cctx);',
                          '\tof_platform_depopulate(&rpdev->dev);\n'
                          '\t/* Stop publishing to callback acquire readers; devm retains the owner. */\n'
                          '\tsmp_store_release(&rpdev->dev.driver_data, NULL);')
    callback = source.index('static int fastrpc_rpmsg_callback(')
    tail = source[callback:]
    tail = replace_once(tail, '\tstruct fastrpc_channel_ctx *cctx = dev_get_drvdata(&rpdev->dev);',
                         '\tstruct fastrpc_channel_ctx *cctx;')
    tail = replace_once(tail, '\tif (!cctx)\n',
                         '\t/* Pair with probe publication of the initialized channel. */\n'
                         '\tcctx = smp_load_acquire(&rpdev->dev.driver_data);\n\tif (!cctx)\n')
    tail = replace_once(tail, '\tspin_lock_irqsave(&cctx->lock, flags);\n\tctx = idr_find',
                         '\tspin_lock_irqsave(&cctx->lock, flags);\n'
                         '\tif (!cctx->ready || !cctx->rpdev) {\n'
                         '\t\tspin_unlock_irqrestore(&cctx->lock, flags);\n'
                         '\t\treturn -ENODEV;\n\t}\n\tctx = idr_find')
    source = source[:callback] + tail
    source = replace_once(source, 'static const struct file_operations fastrpc_fops = {\n',
                          'static const struct file_operations fastrpc_fops = {\n\t.owner = THIS_MODULE,\n')
    source = replace_once(source, '\tplatform_driver_unregister(&fastrpc_cb_driver);\n\tunregister_rpmsg_driver(&fastrpc_driver);',
                          '\tunregister_rpmsg_driver(&fastrpc_driver);\n\tplatform_driver_unregister(&fastrpc_cb_driver);')
    return source


def main():
    PRIVATE.mkdir(exist_ok=True)
    assert not BUILD.exists(), 'Do not replace an existing build/experiment'
    before = snapshot()
    base = (KERNEL / 'drivers/misc/fastrpc.c').read_bytes()
    assert digest(base) == BASE_SHA
    (PRIVATE / 'kernel-before-private.json').write_text(json.dumps(before, indent=2) + '\n')
    (PRIVATE / 'fastrpc-before-private.c').write_bytes(base)
    (PRIVATE / 'fastrpc-before-private.ko').write_bytes((KERNEL / 'drivers/misc/fastrpc.ko').read_bytes())
    new = candidate(base.decode())
    freezer = '''		/* Keep this RPC and its DMA buffers while the invoking task freezes. */
		do {
			err = wait_for_completion_state(&ctx->work,
							TASK_INTERRUPTIBLE | TASK_FREEZABLE);
		} while (err == -ERESTARTSYS && try_to_freeze());'''
    assert freezer in base.decode() and freezer in new
    BUILD.mkdir(parents=True)
    for name, text in [('baseline', base.decode()), ('candidate', new)]:
        folder = BUILD / name
        folder.mkdir()
        (folder / 'fastrpc.c').write_text(text)
        (folder / 'Makefile').write_text('obj-m += fastrpc.o\n')
    patch = make_patch(base.decode(), new)
    (REF / 'fastrpc-publication-lifetime.patch').write_text(patch)
    assert snapshot() == before
    (PRIVATE / 'current-work-private.json').write_text(json.dumps({
        'stage': 227, 'state': 'isolated candidate prepared; unreviewed/unbuilt/uninstalled',
        'full_peripheral_goal_active': True, 'active_build_session': None,
        'runtime_deployed': False, 'phone_changes': False,
        'guard_reference': '/var/lib/samurai/k226-baseline/boot-id-private.txt',
    }, indent=2) + '\n')
    report = {'stage': 227, 'source_before_sha256': digest(base),
              'candidate_source_sha256': digest(new.encode()), 'patch_sha256': digest(patch.encode()),
              'canonical_preserved_files': len(before) - 2, 'canonical_unchanged': True,
              'freezer189_exact_preserved': True, 'runtime_deployed': False,
              'ssr_dma_drain_not_implemented': True}
    (REF / 'fastrpc-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
