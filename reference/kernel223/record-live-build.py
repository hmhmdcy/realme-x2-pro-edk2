from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel223')
state=json.loads((private/'current-work-private.json').read_text());state.update(state='223 paired SOF candidate fae1 verified with64 RAW/RGB frames; original82c/e49/r7-r2 restored; full r8 capture-control snapshot build live',active_build_session=54480,build_state_file=str(private/'r8-build-state-private.json'),protected_original214_snapshot='/home/cy122/x2pro-linux/libcamera214-root/private/libcamera214-before223',candidate_retained_after_terminal='/home/cy122/x2pro-linux/libcamera214-root/work/libcamera223-built',next='Poll54480 without restarting. Do not move /work/libcamera while live. Terminal builder must restore original2142254-file tree. Verify all13 r8/r3 packages and5IPA, test actual capture-time control snapshots with paired fae1 driver, then deploy coherent pair with original82c/r7 rollback retained.',manual_api_future_raw_path_note='RAW-only currently bypasses SWISP configure/start/stats. Do not claim manual/AE APIs complete from RGB tests or merely advertise controls. Need a truthful direct RAW control/metadata path or stats-only processing as well as RGB semantics.')
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
old=(repo/'NEXT-SESSION.md').read_text();archive=repo/'archive/NEXT-SESSION-through222-2026-10-16.md'
if not archive.exists():archive.write_text(old)
start=old.index('2026-10-16');end=old.index('\n\n## 当前部署',start)
old=old[:start]+'2026-10-16，223：配对SOF候选fae1完成64帧RAW/RGB实测，原82c/e49/r7-r2已恢复。r8采集时控制快照完整构建中，session54480；原214源码受保护。[223记录](reference/kernel223/README.md)、[边界](WORKING-BOUNDARIES.md)。全外设goal active。'+old[end:]
start=old.index('- SDK /home/cy122/x2pro-linux/libcamera214-root');end=old.index('\n-',start+2)
old=old[:start]+'''- r8构建session54480；SDK /home/cy122/x2pro-linux/libcamera214-root，原214在/private/libcamera214-before223，当前/work/libcamera是候选副本，活构建时不可移动；终态恢复2254文件/链接，候选保留/work/libcamera223-built。配方/work/libcamera223及samurai-camera-config223，输出/packages223、/packages-config223；产物待验收，手机r7。
'''.rstrip()+old[end:]
start=old.index('- 219真实4MP');end=old.index('\n-',start+2)
old=old[:start]+'- 219真实4MP/实验16MP暗RAW/CPU RGB、帧变化/TPG与DMA同步证据保持，详见219。完整TPG仍普通Bayer，不能验真实Quad颜色，关灯近黑不能单判bug。'+old[end:]
assert len(old.encode())<=6500,len(old.encode());(repo/'NEXT-SESSION.md').write_text(old)
(here/'README.md').write_text('''# 223：捕获缓冲SOF配对与控制快照

2026-10-16，原boot219/Image183/e49/CAMSS82c/完整r7-r2重新认证，当前仍该部署；未重启或刷写。[基线](baseline-validation.json)。

原驱动RAW请求间隔500ms时，缓冲号仍连续0–15，未计入缺少缓冲造成的丢帧。新候选为每个缓冲保存真实SOF号，重排队清有效位，SOF标记尚未开始的最老活动缓冲；缺标记交付buffer error。事件订阅仅限已实现的SM8150/VFE170路径。[补丁](camss-sm8150-paired-sof-candidate.patch)、[构建](sof-candidate-build-validation.json)、[原RAW基线](baseline-raw-gap-validation.json)。

临时模块fae1ed40…完成2MP/4MP各RAW/RGB四组共64帧。四组缓冲号均能在独立事件流找到，SOF至完成时间约12.8–16.9ms；RAW缺缓冲后序号跳到33/19等，未出现缺标记。已恢复原82c loaded-note、媒体图/格式/WP，桌面/PipeWire身份保持，taint及五fault0。[原生结果](paired-sof-native-validation.json)。事件/时间戳不代替实际曝光延迟标定。

libcamera候选在捕获回调按采集序号读取DelayedControls并存入请求的独立快照，统计处理仅使用该快照，保留无frameStart平台的旧路径与请求号IPA索引。[用户态补丁](libcamera-capture-control-snapshot.patch)。需要与配对驱动一起验收，尚未永久部署。

完整r8/config-r3构建session54480进行中；保留全部原13补丁、管线/子包/tuning/YAML和原签名输入，原r7缓存保留。SDK原214已移至/private/libcamera214-before223保护，活构建不可移动当前/work/libcamera；终态恢复，候选保留/work/libcamera223-built。手机仍r7。必须核对13包/5IPA及实际快照生效后再部署。

标准手动曝光/增益/独立模式尚未加入；RAW-only路径目前绕过SWISP配置与统计，也需要正确的控制/元数据链路，不能只验RGB就称完整。后置四摄、GNSS真实fix、蜂窝业务及其余全外设目标继续active。用户关灯/室内窗边，测试只记录数值元数据，不存场景或使用外部照明。
''')
print(json.dumps(dict(stage=223,active_build_session=54480,next_session_bytes=len(old.encode()),phone_deployment_unchanged=True,goal_active=True)))
