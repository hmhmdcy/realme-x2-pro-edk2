"""Sync only reviewed public closeout documents to the local Git checkout."""
from pathlib import Path
import ast
import hashlib
import json
import re
import shutil

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel145'
out = Path('/mnt/e/edk2-samurai-out/kernel145')
mirror = Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
backup = out / 'mirror-before-closeout-private'
assert not backup.exists() and mirror.is_dir()
names = ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'HANDOVER-NEXT.md', 'HANDOVER.md',
         'README.md', 'DOCS-INDEX.md', 'linux-port/README.md',
         'linux-port/docs/HARDWARE-STATUS.md', 'linux-port/docs/00-INDEX.md',
         'linux-port/scripts/docs-health-check.sh',
         'sessions/145-dsi-observation-and-old-build-cleanup.md',
         'sessions/145-dsi-deployment-and-session-closeout.md']

# Clarify the distinction between this failed temporary trace and baseline services.
for name in names:
    if not name.endswith('.md'):
        continue
    path = root / name
    text = path.read_text().replace('临时开机服务和自建trace均不再存在',
                                    '本轮临时开机服务已移除，k145-startup实例不存在')
    path.write_text(text)
path = root / 'sessions/145-dsi-deployment-and-session-closeout.md'
text = path.read_text()
text = text.replace('充电只读驱动仍存在；没有做新的充电控制/温度保护验收。',
                    '充电只读驱动仍存在；没有做新的充电控制/温度保护验收。当前Wi-Fi已关联、BlueZ服务启动，MPSS/ADSP运行，SLPI及传感器供电关闭；本轮未重验无线数据流量或其他硬件。原系统display/radio追踪实例仍开启，本次只清理k145临时记录器，没有关闭原系统观测。')
path.write_text(text)
path = root / 'NEXT-SESSION.md'
text = path.read_text().replace('没有可用于分析的145启动trace。',
                                '没有可用于分析的145启动trace；原系统display/radio实例仍开启，其数据不等同于本次失败的早期采集。')
path.write_text(text)
path = root / 'linux-port/docs/HARDWARE-STATUS.md'
text = path.read_text()
rows = {
    'Wi-Fi': '| Wi-Fi | 当前145已关联无线网络、MPSS运行；130历史暖启动5180MHz/网关/HTTPS通过 | 本轮未重新验数据流量；物理冷启动/休眠/长稳及历史reason7仍开放，原profile/固件/校准保持 |',
    '蓝牙': '| 蓝牙 | 当前145 BlueZ服务已启动；历史LE/BR/EDR/混合扫描通过，本轮未配对或扫描 | 历史UART重组错误仍未解决；配对/传输、物理冷启动/休眠/长稳待办 |',
    '蜂窝网络/数据': '| 蜂窝网络/数据 | 当前145 MPSS运行、132的IPA模块和770模块树核验通过；历史ModemManager sim-missing边界保留 | 本轮未验移动数据或通话，clock/ICC压力、SSR/冷启动/休眠/长稳待办 |',
    '摄像头': '| 摄像头 | 历史126内部TPG3帧真实DMA/IRQ/raw10/电源恢复通过；当前145的132设备树与770模块保持，物理camera未验收 | 外部PHY/sensor/PM8008/HAL及物理stream、颜色/位深/多模式与应用待办 |',
    '其它传感器': '| 其它传感器 | 早期STK3331/MMC5603X独立样本证据保留；当前145 SLPI offline，传感器vdd/vddio=0 | 历史两版功能不能合并认定；磁力计矩阵/准确度、加速度/陀螺仪、lux和日常功能待办 |'
}
for label, replacement in rows.items():
    text, count = re.subn(r'^\| ' + re.escape(label) + r' \|.*$', replacement, text, count=1, flags=re.M)
    assert count == 1
path.write_text(text)

# HANDOVER frontmatter hash follows its edited body.
path = root / 'HANDOVER.md'
text = path.read_text()
body = text.split('---', 2)[-1]
text = re.sub(r'^content_hash: .*$', 'content_hash: "' + hashlib.sha256(body.encode()).hexdigest() + '"', text, count=1, flags=re.M)
path.write_text(text)
for path in ref.glob('*.py'):
    ast.parse(path.read_text())
for name in ['NEXT-SESSION.md', 'sessions/145-dsi-deployment-and-session-closeout.md']:
    text = (root / name).read_text()
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' not in target and not target.startswith('#'):
            assert ((root / name).parent / target.split('#')[0]).is_file(), target
assert '手机#145/software132' in (root / 'NEXT-SESSION.md').read_text()
assert '临时开机服务已移除' in (root / 'NEXT-SESSION.md').read_text()
assert not (root / 'NEXT-SESSION.md').read_text().startswith('手机140')

names += [str(path.relative_to(root)) for path in sorted(ref.iterdir()) if path.is_file()]
assert len(names) == len(set(names))
assert all('private' not in Path(name).name and (root / name).stat().st_size < 200000 for name in names)
backup.mkdir(mode=0o700)
changed = 0
for name in names:
    source = root / name
    dest = mirror / name
    if dest.exists() and source.read_bytes() == dest.read_bytes():
        continue
    if dest.exists():
        saved = backup / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(dest, saved)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    assert source.read_bytes() == dest.read_bytes()
    changed += 1
report = dict(stage=145, public_files_verified=len(names), local_mirror_changed_files=changed,
    public_files_byte_identical=True, new_handover_links_verified=True,
    public_python_syntax_verified=True, private_artifacts_not_copied=True,
    preexisting_mirror_files_backed_up=True, committed=False, pushed=False,
    baseline_display_radio_traces_preserved=True,
    goal_complete=False)
out.joinpath('closeout-sync-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
