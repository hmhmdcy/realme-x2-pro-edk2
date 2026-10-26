"""Accept only the kernel's exact generated LDO name metadata; retain policy."""
from pathlib import Path
import difflib
import hashlib
import json

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel236')
old_path = R.parent / 'kernel235/qcom-pm8008-imx319-lab.c'
old = old_path.read_text()
assert hashlib.sha256(old.encode()).hexdigest() == 'ce5c15bc324013629f5a89ff7f5e60f7926f269413c2f4e8bed864ba7f6c5b9e'
needle = '''\t\t\tconst char *name = property->name;

\t\t\tif (strcmp(name, "regulator-name")'''
replacement = '''\t\t\tconst char *name = property->name;

\t\t\t/* OF unflatten adds this standard metadata to every LDO. */
\t\t\tif (!strcmp(name, "name")) {
\t\t\t\tconst char *expected = index == 0 ? "ldo1" : "ldo4";

\t\t\t\tif (property->length != 5 || !property->value ||
\t\t\t\t    memcmp(property->value, expected, 5))
\t\t\t\t\tgoto put_child;
\t\t\t\tcontinue;
\t\t\t}
\t\t\tif (strcmp(name, "regulator-name")'''
assert old.count(needle) == 1
new = old.replace(needle, replacement)
assert not (R / old_path.name).exists()
(R / old_path.name).write_text(new)
header = R.parent / 'kernel235/qcom-pm8008-imx319-lab.h'
(R / header.name).write_bytes(header.read_bytes())
(R / 'pm8008-live-of-name.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
    fromfile='a/drivers/regulator/qcom-pm8008-imx319-lab.c', tofile='b/drivers/regulator/qcom-pm8008-imx319-lab.c')))
functions = lambda text: text[text.index('static int pm8008_lab_valid'):text.index('/* Reject extra outputs')]
assert functions(old) == functions(new)
report = dict(stage=236, before_sha256=hashlib.sha256(old.encode()).hexdigest(),
              candidate_sha256=hashlib.sha256(new.encode()).hexdigest(), shared_header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
              only_dt_metadata_validation_changed=True, all_465_tested_power_callbacks_byte_identical=True,
              voltage_masks_fault_lifetime_reset_and_q_policy_unchanged=True, no_phone_operation=True)
(R / 'lab-fix-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state_path = P / 'current-work-private.json'
state = json.loads(state_path.read_text())
state.update(state='235 boot actually flashed once;236 new identity confirmed, first observer terminal1 because lab DT whitelist rejects real OF-generated name; no rear rails registered/ID not passed',
             guard='/var/lib/samurai/k236-runtime/boot-id-private.txt', transition_pending=False,
             active_native_context=None, active_native_session=None,
             next='Build/test strict OF-name fix, replace only unbound lab module with guarded transaction; preserve live P/Q/provider; do not repeat flash or observer',
             first_hardware_candidate_rejection_preserved=True, rear_id_verified=False)
state_path.write_text(json.dumps(state, indent=2) + '\n')
root = R.parents[1] / 'NEXT-SESSION.md'
before_checkpoint = root.read_text()
(P / 'pretransition-checkpoint-private.md').write_text(before_checkpoint)
old_intro = '2026-10-16，236切换工作进行中。235后摄候选已实现/编译/暂存；236新基线和9份精确路径工具校验通过。实际过渡阶段、活动worker和请求marker优先读私人236/current-work-private.json及原生状态；不能按旧交接重发操作。'
new_intro = '2026-10-16，236新启动已确认：fresh fastboot核验后只刷235 boot一次、重启一次。首个observer terminal1，lab白名单拒绝内核合成name，P两路未注册/后摄未绑定、ID未验；taint/fault0。已定位并准备最小修正，实际阶段优先读私人236/current-work-private.json；不重复切换/刷写/observer。'
assert old_intro in before_checkpoint
text = before_checkpoint.replace(old_intro, new_intro)
text = text.replace('- 切换前仍233启动，guard /var/lib/samurai/k233-runtime/boot-id-private.txt；新k236-baseline已与其当场核对，原k233-baseline属于更早boot，不能拿来核身份。', '- 当前guard /var/lib/samurai/k236-runtime/boot-id-private.txt，所有233及更早guard失效；k236-baseline仅作切换前证据。')
text = text.replace('- 运行boot232 45f398f2…/96MiB、DTB7e8345ae…，Image183 bfa72dd9…/logdump183 e73754c7…。运行MFD232 f633467f…/20520B与provider2223f337…/9744B仍绑定P/Q，地址模式Y，无P secondary/children。', '- 当前boot235 44c6a215…/96MiB/DTB469e1456…，Image183/logdump183保持且原生分区读回通过。MFD6021a359…、provider及P/Q绑定，P secondary/特殊lab child存在但child未绑定；旧lab22c28914…与IMX319 176f68d7…已加载。前摄改为9-0010/suspended，后摄7-0010未绑定；三DSP恢复running。')
text = text.replace('先观察已有236 quiesce worker/终态；quiesce成功后执行一次Linux→bootloader，fresh fastboot身份/产品/几何后只刷锁定235 boot一次。未明切换不重复。新boot建立k236-runtime guard并核分区/789文件/默认与加载note/P两路/ID/自动挂起，再做有界RAW RAM统计和掉电回收/前摄回归。', '236 quiesce terminal0、flash/reboot各一次已完成；首个runtime observer terminal1保留，不重跑。root只读实际OF验证ldo1/4含name，源码fdt.c确认合成语义；最小修正仅允许并核验name=ldo1/ldo4及长度/NUL，不放宽供电字段。构建/真实DT-validator模型通过后，只替换未绑定lab模块，保留P/Q/provider；再观察同新boot的ID/自动挂起及后续RAW RAM统计/前摄回归。')
assert len(text.encode()) <= 6500
root.write_text(text)
print(json.dumps(report))
