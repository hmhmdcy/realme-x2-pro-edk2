from pathlib import Path
import json
import tarfile

root = Path('E:/RealmeX2Pro edk2')
private = Path('E:/edk2-samurai-out/kernel182')
with tarfile.open(private / 'k182-all-private.tar.gz') as t:
    final = json.loads(t.extractfile('k182-final/validation.json').read())
assert final['stage'] == 182 and final['kernel_build'] == 181 and final['same_boot']
assert final['taint'] == 0 and not any(final['initial_boot_and_full_current_ring_fault_counts'].values())
(root / 'reference/kernel182/final-validation.json').write_text(json.dumps(final, indent=2) + '\n', encoding='utf-8')
next_path = root / 'NEXT-SESSION.md'
next_text = next_path.read_text(encoding='utf-8')
start = next_text.index('最后核对：')
end = next_text.index('\n\n', start)
next_text = next_text[:start] + '''最后核对：2026-10-14，本轮182继续已部署kernel181。初启动、一次受控ADSP停启及活跃录音中一次合成crash报告后的自动恢复通过，原录音客户端恢复后检出右编码音。原生/桌面左右播放已有证据、171用户双组滴声确认。完整goal active：实物耳机、真实watchdog、活跃播放恢复、长PM/跨启动/音质保护仍开放；用户暂无耳机，不重复问。规则见[WORKING-BOUNDARIES](WORKING-BOUNDARIES.md)。''' + next_text[end:]
next_text = next_text.replace('| 181最终 |', '| 181历史最终 |')
marker = '| 初启动与ADSP |'
position = next_text.index(marker)
next_text = next_text[:position] + '''| 182最新 | 同181 boot2514.86秒taint0，自动card/HiFi恢复、原parecord连接新Mic，右编码相关0.9696；PCM关、功放18/18静音、16控件恢复、五consumer各1、两map/一MCLK、cache-only=N，所列20项全boot0、NV/分区/模块132核验 |
''' + next_text[position:]
next_text = next_text.replace('依据：[181]', '依据：[182](reference/kernel182/README.md)、[181]')
next_text = next_text.replace('1. 已知受控ADSP重启缺陷现已一次通过，但要补活跃流/真实自动crash、较长和重复PM、跨启动；先读181当前收据和源码，不重跑已过场景只为扩大数量。保留完整音频目标。',
'''1. 182只向debugfs注入一次合成MMU故障报告，原桌面录音自动恢复；不是实际DSP watchdog故障。观察card资源缺口0.3615秒，之后2.2069秒capture RUNNING。原report 7.927秒字段包含播放/等待，派生摘要更名、原件保留。下一步活跃播放恢复、较长重复PM、跨启动和音质/保护；不重跑已过场景只为增加数量。''')
next_text = next_text.replace('当前/回退私件在E:/edk2-samurai-out/kernel181、180、176。', '182证据私件在E:/edk2-samurai-out/kernel182；当前/回退镜像在181、180、176。')
next_text = next_text.replace('原176十文件加PDR。当前MFD181源5c4469fb…、PDR180源9bed7403…，其余九音频源及15显示源163保持；', 'MFD181源5c4469fb…、PDR180源9bed7403…，九其它音频源及15显示源163保持；')
next_text = next_text.replace('176的10次重绑、18旧FD EIO、177两例短时s2idle', '176的重绑及177短时s2idle')
audio_text = '''在 E:\\RealmeX2Pro edk2 继续原生Linux音频修复，完整goal active。先读NEXT-SESSION、WORKING-BOUNDARIES、HARDWARE-STATUS和reference/kernel182/README.md，再读181/180/179/178、177/176及171线路与人工听音。

本轮182没有内核/固件/UCM改动，继续kernel181/logdump181、boot/DTB172、模块/软件132、Mesa149、UCM173。#181 Oct14 22:56:05 CST；logdump 56aa1c463d118f9de8d5dbd2cad3dc6b2ab1ff9f36d4027c77d457520b702a55，Image ae0eb8e0de80540cfe4349870020c1370534975bc30d90190c59afdf1d6afd11。WSL kernel136 tracked11完整哈希见181 build；MFD181/PDR180、九其它音频源及15显示源163保持，builtin及770模块132兼容。下次切换新取身份，不使用旧preflash。

171用户确认两组滴声来自手机。181初启动及一次受控ADSP offline→running通过，自动HiFi/录音恢复、资源回收/重建、旧FD EIO，无手工重绑；原生左右相关0.9574/0.9327，桌面0.9575/0.9942，功放关闭参考区分、无削顶。音乐/人声、完整频响和声压/保护未验收。

182在原parecord、Mic PCM RUNNING时向debugfs crash写入一次0。入口调用rproc_report_crash，合成MMU故障报告，不是实际固件watchdog。recovery enabled及coredump默认disabled保持。自动重建card/两map/PulseHiFi，五consumer恢复，2旧FD EIO；原source-output从旧Mic连接到新Mic，未替换客户端。17项测试窗口故障0，预期crash/handler/recovery各1。原录音检出恢复后右1511Hz编码音相关0.96958、开关差40.71dB、相对同boot181原生amp-off参考20.40dB，无削顶，source volume/mute相同；没有独立桌面amp-off实验，不证明故障期间连续无损。

时间线25ms名义采样观察card资源缺口0.3615秒，之后2.2069秒capture RUNNING。原report recovery_latency_seconds=7.927实际包含测试音播放和等待，字段误名；原件未改，派生摘要改名crash_to_after_playback_and_wait_elapsed_seconds。原录音位置不当墙钟时间。

182最终2514.86秒同181 boot、taint0、ADSP running，单CARD/alsa-card和HiFi，PCM关、双功放18/18关闭静音、16保存控件恢复、五consumer各1、两map/一MCLK、main cache-only=N、NGD suspended；NV/persist/boot/logdump/770模块核验。ring从0秒且含#181 banner，所列20项全boot0。预期crash日志及可选SoundWire child缺of_node提示保留，不扩大成所有整机问题清零。身份/日志/录音在私人182包，181镜像保持。

180 PDR修复锁外事务/回调、peer/世代/通知序列、旧注册明确取消、退役对象寿命与release同步；181同步停parent IRQ后，仅DOWN对main MAPLE map设cache-only做软件IRQ清理，随后销毁，不同步/重放；UP移除仍真实IO，IF无缓存策略保持。118实际函数host场景/17负对照及实机证据见181。178失败IRQ27720/config144/mask12/ASoC6/PDR2及启动PDR3/config8/mask1，180停启config72/mask6均保留；181/182通过不改历史。

下一步活跃播放恢复、当前181较长重复PM/跨启动、音乐/人声/瞬态/保护；真实watchdog和所有SSR仍开放。用户暂无耳机，耳机/耳麦/按钮待实物，不重复问。callaudiod负责端口，不补载Pulse自动切换模块。一加hotdog UCM/麦克风测量方法与SD1/GPIO140对照已用于171，本机接线以Realme19781为准，不套TFA9874参数到MAX98937。

180 F1无回执仍Linux/解冻，重绑EUD未恢复，原因未定；Linux RESTART2路径180/181成功，须新身份/完整停机/冻结，按本树CSR_EUD_EN关闭和单次bootloader重启，再看真实fastboot。未知切换不重复。回退/边界见NEXT，NV/校准/私人数据、电池保护、蓝牙只扫描及振动不加脉冲保持；其它整机问题按HARDWARE清单。
'''
status_path = root / 'linux-port/docs/HARDWARE-STATUS.md'
status = status_path.read_text(encoding='utf-8')
start = status.index('用途：'); end = status.index('\n\n', start)
status = status[:start] + '''用途：当前硬件验收清单。最后核对：2026-10-14，本轮182继续kernel181/logdump181，boot/DTB172、software/modules132/Mesa149/UCM173保持。初启动、受控ADSP停启及一次活跃录音合成crash后的自动恢复通过，原客户端恢复后拾音检出。完整音频goal active，实物耳机/真实watchdog/活跃播放恢复/长PM/跨启动/音质保护仍开放。显示165/GPU149保持。以[182](../../reference/kernel182/README.md)、[181](../../reference/kernel181/README.md)、[180失败](../../reference/kernel180/README.md)、[171人工听音](../../reference/kernel171/README.md)为准，规则见[边界](../../WORKING-BOUNDARIES.md)。''' + status[end:]
lines = status.splitlines()
for i, line in enumerate(lines):
    if line.startswith('| 音频 |'):
        lines[i] = '''| 音频 | 171人工双组滴声；181 PDR/IRQ修复部署，初启动/受控ADSP停启通过、原生/桌面左右检出。182活跃录音中单次合成crash自动重建card/HiFi、原客户端连接新Mic并检出右编码0.96958；2515秒taint0、所列20项全boot0，PCM关、功放18/18静音、16控件恢复、五consumer各1、两map/一MCLK、cache-only=N | 耳机/耳麦/按钮、真实DSP watchdog、活跃播放恢复、长PM/跨启动、音质/瞬态/保护开放。用户暂无耳机。178 IRQ27720/config144/mask12/ASoC6/PDR2及启动PDR3/config8/mask1、180 config72/mask6失败保留，不被新通过覆盖 |'''
status = '\n'.join(lines) + '\n'
updates = [(next_path, next_text, 6500), (root / 'AUDIO-NEXT-SESSION-PROMPT.txt', audio_text, 4000),
           (status_path, status, None)]
for path, text, limit in updates:
    assert limit is None or len(text.encode('utf-8')) <= limit, (path.name, len(text.encode('utf-8')))
    assert not (private / (path.name + '-before182-private')).exists()
for path, text, limit in updates:
    (private / (path.name + '-before182-private')).write_bytes(path.read_bytes())
    path.write_text(text, encoding='utf-8', newline='\n')
print(json.dumps({p.name: len(t.encode('utf-8')) for p, t, _ in updates}))
