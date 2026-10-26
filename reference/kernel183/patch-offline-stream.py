from pathlib import Path
import difflib
import hashlib
import json
import os
import subprocess

os.umask(0o077)
ref = Path(__file__).resolve().parent
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel183')
out.mkdir(mode=0o700, exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = json.loads((ref.parent / 'kernel181/source-validation.json').read_text())
for name, digest in baseline['source_sha256'].items():
    assert sha(k / name) == digest, name
changed = {}
def edit(name, old, new):
    text = changed.get(name, (k / name).read_text())
    assert text.count(old) == 1, (name, old[:80])
    changed[name] = text.replace(old, new)

edit('drivers/slimbus/slimbus.h', ' * @enable_stream: This function pointer implements controller-specific procedure',
     ' * @is_online: Optional non-sleeping transport availability query. Sleeping\n'
     ' *\tcontrollers remain online if normal runtime resume can reach the device.\n'
     ' * @enable_stream: This function pointer implements controller-specific procedure')
edit('drivers/slimbus/slimbus.h', '\tint\t\t(*enable_stream)(struct slim_stream_runtime *rt);',
     '\tbool\t\t(*is_online)(struct slim_controller *ctrl);\n'
     '\tint\t\t(*enable_stream)(struct slim_stream_runtime *rt);')
edit('include/linux/slimbus.h', '/* SLIMbus Stream apis */',
     'bool slim_device_is_online(struct slim_device *sdev);\n\n/* SLIMbus Stream apis */')
edit('include/linux/slimbus.h', 'int slim_stream_free(struct slim_stream_runtime *stream);',
     'int slim_stream_abort(struct slim_stream_runtime *stream);\nint slim_stream_free(struct slim_stream_runtime *stream);')
edit('drivers/slimbus/core.c', 'EXPORT_SYMBOL_GPL(slim_report_absent);', '''EXPORT_SYMBOL_GPL(slim_report_absent);

/**
 * slim_device_is_online() - Check whether a device has a usable transport
 * @sdev: Device whose logical address and transport are being checked
 *
 * This is a non-sleeping snapshot, not a lifetime or transaction lock. A
 * suspended transport is online if normal runtime resume can reach it.
 */
bool slim_device_is_online(struct slim_device *sdev)
{
	struct slim_controller *ctrl = sdev->ctrl;

	if (!ctrl || READ_ONCE(sdev->status) != SLIM_DEVICE_STATUS_UP ||
	    !READ_ONCE(sdev->is_laddr_valid))
		return false;

	return !ctrl->is_online || ctrl->is_online(ctrl);
}
EXPORT_SYMBOL_GPL(slim_device_is_online);''')
edit('drivers/slimbus/stream.c', 'EXPORT_SYMBOL_GPL(slim_stream_unprepare);', '''EXPORT_SYMBOL_GPL(slim_stream_unprepare);

/**
 * slim_stream_abort() - Discard local stream state after transport loss
 * @stream: Stream whose device or transport has gone offline
 *
 * The caller serializes this with prepare and trigger operations. No bus
 * command is sent, and no successful hardware stop is implied. A live device
 * must use the ordinary disable/unprepare sequence instead.
 *
 * Return: zero after local cleanup, or -EBUSY if the device is online.
 */
int slim_stream_abort(struct slim_stream_runtime *stream)
{
	if (slim_device_is_online(stream->dev))
		return -EBUSY;

	kfree(stream->ports);
	stream->ports = NULL;
	stream->num_ports = 0;

	return 0;
}
EXPORT_SYMBOL_GPL(slim_stream_abort);''')
edit('drivers/slimbus/qcom-ngd-ctrl.c', 'static int qcom_slim_ngd_get_laddr(struct slim_controller *ctrl,', '''static bool qcom_slim_ngd_is_online(struct slim_controller *sctrl)
{
	struct qcom_slim_ngd_ctrl *ctrl =
		container_of(sctrl, struct qcom_slim_ngd_ctrl, ctrl);

	/* QMI loss precedes report_absent and codec removal during SSR. */
	return READ_ONCE(ctrl->state) != QCOM_SLIM_NGD_CTRL_DOWN &&
		READ_ONCE(ctrl->registered) && READ_ONCE(ctrl->qmi.handle);
}

static int qcom_slim_ngd_get_laddr(struct slim_controller *ctrl,''')
edit('drivers/slimbus/qcom-ngd-ctrl.c', '\tctrl->ctrl.get_laddr = qcom_slim_ngd_get_laddr;',
     '\tctrl->ctrl.is_online = qcom_slim_ngd_is_online;\n\tctrl->ctrl.get_laddr = qcom_slim_ngd_get_laddr;')
edit('sound/soc/codecs/wcd934x.c', 'static int wcd934x_trigger(struct snd_pcm_substream *substream,', '''static int wcd934x_slim_stop(struct wcd934x_codec *wcd,
			     struct wcd_slim_codec_dai_data *dai_data)
{
	int ret = 0, cleanup;

	if (!slim_device_is_online(wcd->sdev))
		goto abort;

	/* Mask FIFO/port-closed events before disconnecting a live bus. */
	ret = wcd934x_slim_port_interrupts(wcd, dai_data, false);
	if (ret == -ENOTCONN && !slim_device_is_online(wcd->sdev))
		goto abort;
	cleanup = slim_stream_disable(dai_data->sruntime);
	if (!ret)
		ret = cleanup;
	if (cleanup == -ENOTCONN && !slim_device_is_online(wcd->sdev))
		goto abort;
	cleanup = slim_stream_unprepare(dai_data->sruntime);
	if (!ret)
		ret = cleanup;
	cleanup = wcd934x_slim_port_clear(wcd, dai_data);
	if (!ret)
		ret = cleanup;
	if (cleanup == -ENOTCONN && !slim_device_is_online(wcd->sdev))
		goto abort;

	return ret;
abort:
	cleanup = slim_stream_abort(dai_data->sruntime);
	return ret && ret != -ENOTCONN ? ret : cleanup;
}

static int wcd934x_trigger(struct snd_pcm_substream *substream,''')
edit('sound/soc/codecs/wcd934x.c', '\tint ret = 0, cleanup;\n\n\tswitch (cmd)', '\tint ret = 0;\n\n\tswitch (cmd)')
edit('sound/soc/codecs/wcd934x.c', '\tcase SNDRV_PCM_TRIGGER_PAUSE_RELEASE:\n\t\tret = wcd934x_slim_port_interrupts',
     '\tcase SNDRV_PCM_TRIGGER_PAUSE_RELEASE:\n'
     '\t\tif (!slim_device_is_online(wcd->sdev)) {\n'
     '\t\t\tret = -ENOTCONN;\n\t\t\tbreak;\n\t\t}\n'
     '\t\tret = wcd934x_slim_port_interrupts')
old = '''		/* Mask FIFO/port-closed events before disconnecting the bus. */
		ret = wcd934x_slim_port_interrupts(wcd, dai_data, false);
		cleanup = slim_stream_disable(dai_data->sruntime);
		if (!ret)
			ret = cleanup;
		cleanup = slim_stream_unprepare(dai_data->sruntime);
		if (!ret)
			ret = cleanup;
		cleanup = wcd934x_slim_port_clear(wcd, dai_data);
		if (!ret)
			ret = cleanup;'''
edit('sound/soc/codecs/wcd934x.c', old, '\t\tret = wcd934x_slim_stop(wcd, dai_data);')
before = {}
diffs = []
for name, text in changed.items():
    path = k / name
    old_text = path.read_text()
    before[name] = sha(path)
    backup = out / ('before183-' + name.replace('/', '_') + '-private')
    assert not backup.exists(), backup
    backup.write_bytes(path.read_bytes())
    diffs.extend(difflib.unified_diff(old_text.splitlines(True), text.splitlines(True),
                                    fromfile='a/' + name, tofile='b/' + name))
for name, text in changed.items():
    (k / name).write_text(text)
(out / 'config-before-private').write_bytes((k / '.config').read_bytes())
patch = '''Subject: [PATCH] slimbus: discard offline WCD streams after transport loss

An SSR can close QMI before device-status callbacks remove the codec. An
active capture STOP then tries interface-register and channel transactions
over the disconnected transport. Expose its availability and release local
stream storage explicitly; preserve ordinary live cleanup and its errors.

---
''' + ''.join(diffs)
(ref / 'offline-stream-abort.patch').write_text(patch)
result = subprocess.run(['scripts/checkpatch.pl', '--no-tree', '--no-signoff', str(ref / 'offline-stream-abort.patch')],
                        cwd=k, capture_output=True)
(out / 'checkpatch-private.log').write_bytes(result.stdout + result.stderr)
subprocess.run(['git', 'diff', '--check'], cwd=k, check=True)
tracked = set(baseline['source_sha256']) | {'drivers/slimbus/stream.c'}
report = dict(stage=183, baseline_kernel=181, modified_this_stage=list(changed), before_sha256=before,
              source_sha256={name: sha(k / name) for name in sorted(tracked)},
              checkpatch_pass=result.returncode == 0, build_and_runtime_pending=True,
              main_and_interface_regmap_cache_policies_unchanged=True,
              offline_stream_abort_is_software_cleanup_not_hardware_success=True,
              pdr180_and_mfd181_preserved=True)
(ref / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(changed=list(changed), checkpatch_returncode=result.returncode)))
assert result.returncode == 0, result.stdout.decode(errors='replace')
