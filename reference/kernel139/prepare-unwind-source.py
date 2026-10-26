from pathlib import Path
import difflib
import hashlib
import json
import os
import runpy
import subprocess

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel139'
out = Path('/mnt/e/edk2-samurai-out/kernel139')
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert os.geteuid() == 0 and not out.exists()
assert sha(k / 'arch/arm64/boot/Image') == 'f7d1367af3b6ff9ad710e268f7f6d54d3cfface72e43ac9d7ee5d99dc0cd552c'
out.mkdir(mode=0o700)
(out / 'source137-before-private.patch').write_bytes(subprocess.check_output(['git', '-C', str(k), 'diff', '--binary']))
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
base = Path('/home/cy122/pmos-samurai-kernel118/power132/kernel')
assert sha(base / 'arch/arm64/boot/Image') == '2b903902f9f5ab64bd663753fb1c6c4e925aa661881e7aac1cf5481657a72537'
# Reuse storage, restore the rejected candidate's six deltas from stable132.
restored = ['drivers/gpu/drm/msm/msm_gpu_trace.h', 'drivers/gpu/drm/msm/msm_gem_vma.c',
            'drivers/gpu/drm/msm/adreno/a6xx_gpu.c', 'drivers/mfd/wcd934x.c',
            'drivers/dma/qcom/bam_dma.c', 'drivers/slimbus/qcom-ngd-ctrl.c']
for name in restored:
    (out / (Path(name).name + '.137-before-private')).write_bytes((k / name).read_bytes())
    (k / name).write_bytes((base / name).read_bytes())
assert subprocess.check_output(['git', '-C', str(k), 'diff', '--binary']) == subprocess.check_output(['git', '-C', str(base), 'diff', '--binary'])

def replace(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new)

changes = {}
name = 'drivers/slimbus/qcom-ngd-ctrl.c'
old = (k / name).read_text()
new = replace(old, '\t\tdev_err(ctrl->dev, "unable to prepare channel\\n");',
              '\t\t/* tx_lock serializes reservations; this slot was never queued. */\n'
              '\t\tdesc->comp = NULL;\n\t\tctrl->tx_tail = index;\n'
              '\t\tdev_err(ctrl->dev, "unable to prepare channel\\n");')
start = new.index('static int qcom_slim_ngd_xfer_msg(')
end = new.index('static int qcom_slim_ngd_xfer_msg_sync(', start)
fn = new[start:end]
fn = replace(fn, '\tif (txn->dt == SLIM_MSG_DEST_ENUMADDR)\n\t\treturn -EPROTONOSUPPORT;',
             '\tif (txn->dt == SLIM_MSG_DEST_ENUMADDR) {\n\t\tret = -EPROTONOSUPPORT;\n\t\tgoto err_free_tid;\n\t}')
fn = replace(fn, '\t\tdev_err(ctrl->dev, "msg exceeds HW limit\\n");\n\t\treturn -EINVAL;',
             '\t\tdev_err(ctrl->dev, "msg exceeds HW limit\\n");\n\t\tret = -EINVAL;\n\t\tgoto err_free_tid;')
reserve = '''\tpbuf = qcom_slim_ngd_tx_msg_get(ctrl, txn->rl, &tx_sent);
\tif (!pbuf) {
\t\tdev_err(ctrl->dev, "Message buffer unavailable\\n");
\t\treturn -ENOMEM;
\t}

'''
fn = replace(fn, reserve, '')
fn = replace(fn, '\t/* HW expects length field to be excluded */',
             '\tmutex_lock(&ctrl->tx_lock);\n'
             '\tpbuf = qcom_slim_ngd_tx_msg_get(ctrl, txn->rl, &tx_sent);\n'
             '\tif (!pbuf) {\n\t\tdev_err(ctrl->dev, "Message buffer unavailable\\n");\n'
             '\t\tret = -ENOMEM;\n\t\tgoto err_unlock;\n\t}\n\n'
             '\t/* HW expects length field to be excluded */')
fn = replace(fn, '''\tmutex_lock(&ctrl->tx_lock);
\tret = qcom_slim_ngd_tx_msg_post(ctrl, pbuf, txn->rl);
\tif (ret) {
\t\tmutex_unlock(&ctrl->tx_lock);
\t\treturn ret;
\t}''', '''\tret = qcom_slim_ngd_tx_msg_post(ctrl, pbuf, txn->rl);
\tif (ret)
\t\tgoto err_unlock;''')
fn = replace(fn, '\tmutex_unlock(&ctrl->tx_lock);\n\treturn 0;\n}',
             '\tmutex_unlock(&ctrl->tx_lock);\n\treturn 0;\n\n'
             'err_unlock:\n\tmutex_unlock(&ctrl->tx_lock);\n'
             'err_free_tid:\n'
             '\t/* Direct user-message callers own their TID and PM error unwind. */\n'
             '\tif ((usr_msg || slim_tid_txn(txn->mt, txn->mc)) && txn->tid) {\n'
             '\t\tslim_free_txn_tid(sctrl, txn);\n\t\ttxn->tid = 0;\n\t}\n'
             '\treturn ret;\n}')
new = new[:start] + fn + new[end:]
changes[name] = (old, new)
name = 'drivers/slimbus/messaging.c'
old = (k / name).read_text()
new = replace(old, '\t/* Initialize tid to invalid value */\n\ttxn->tid = 0;\n', '')
new = replace(new, '\tbool need_tid = false, clk_pause_msg = false;\n\tint ret;\n\tunsigned long time_left;\n',
              '\tbool need_tid = false, clk_pause_msg = false;\n\tint ret;\n\tunsigned long time_left;\n\n'
              '\t/* Also invalid on errors before TID allocation. */\n\ttxn->tid = 0;\n')
new = replace(new, '\t\tret = slim_alloc_txn_tid(ctrl, txn);\n\t\tif (ret)\n\t\t\treturn ret;',
              '\t\tret = slim_alloc_txn_tid(ctrl, txn);\n\t\tif (ret)\n\t\t\tgoto slim_xfer_err;')
changes[name] = (old, new)
patch = []
for name, (old, new) in changes.items():
    (out / (Path(name).name + '.132-before-private')).write_text(old)
    (k / name).write_text(new)
    patch.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='a/' + name, tofile='b/' + name))
(ref / 'ngd-unsubmitted-unwind.patch').write_text(''.join(patch))
report = dict(stage=139, baseline=132, only_changed_files=list(changes),
              source137_archived=True, rejected137_and136_deltas_removed=True,
              reserve_serialized_before_message_assembly=True,
              only_unsubmitted_slot_tail_rewound=True, completion_cleared=True,
              core_and_converted_tid_cancelled=True, direct_user_tid_ownership_preserved=True,
              tid_allocation_failure_pm_unwound=True, early_tid_initialized=True,
              queued_timeout_behavior_unchanged=True, dma_allocation_policy_unchanged=True,
              display_gpu_charge_behavior_unchanged=True, goal_complete=False,
              files={name: hashlib.sha256(new.encode()).hexdigest() for name, (_, new) in changes.items()},
              related_unmerged_discussion='https://lkml.iu.edu/2609.2/05810.html',
              discussion_test_limit='https://lkml.iu.edu/2610.0/02660.html')
(ref / 'unwind-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K139_BASE132_TWO_FILE_UNSUBMITTED_UNWIND_SOURCE_PREPARED', flush=True)
