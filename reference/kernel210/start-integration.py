from pathlib import Path
import json,os,shutil
os.umask(0o077)
here=Path(__file__).resolve().parent;repo=here.parents[1]
private=Path('/mnt/e/edk2-samurai-out/kernel210')
archive=repo/'archive/NEXT-SESSION-through209-2026-10-15.md'
assert not archive.exists();shutil.copyfile(repo/'NEXT-SESSION.md',archive)
plan=dict(stage=210,state='Source/device baseline backed up. Baseline DTB semantically equals deployed204. No210 product install/reboot yet.',gnss_environment='User explicitly reports indoors by window. No outdoor test available; weak sky cannot be excluded. Do not repeat UTC/CNR diagnostics unchanged.',next='Integrate proven200 front sensor with static DTS and persistent config/modules; verify intended-only DT delta, imports and preserved custom modules. Prepare guarded boot only after fresh device checks.',transport='reference/kernel210/host.py',guard='/var/lib/samurai/k210-baseline/boot-id-private.txt',transition_pending=False)
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
text=(repo/'NEXT-SESSION.md').read_text()
old='2026-10-15，阶段209，完整外设goal active。UTC不确定度单变量对照未改善接收器约6秒报告或真实收星；候选未部署，产品仍207状态。已核对常态摄像头缺失的DTS与模块，下一步推进持久化相机接入。209没有重启/刷写。[209报告](reference/kernel209/README.md)、[完整208快照](archive/NEXT-SESSION-through208-2026-10-15.md)、[边界](WORKING-BOUNDARIES.md)。'
assert old in text
text=text.replace(old,'2026-10-15，阶段210进行中，完整外设goal active。已备份全部内核改动和构建产物；源码基线DTB与实际204部署树语义一致。正在把200成功取流的前摄接入常规DTS和模块配置；210尚未安装或重启。[210进展](reference/kernel210/README.md)、[完整209快照](archive/NEXT-SESSION-through209-2026-10-15.md)、[边界](WORKING-BOUNDARIES.md)。')
text=text.replace('当前运输 `reference/kernel209/host.py`，guard `/var/lib/samurai/k209-baseline/boot-id-private.txt`','当前运输 `reference/kernel210/host.py`，guard `/var/lib/samurai/k210-baseline/boot-id-private.txt`')
old='已异步询问手机摆放条件，尚未得到答复，不能假定环境；继续相机工作不依赖该回复。'
assert old in text;text=text.replace(old,'用户已明确答复手机在室内窗边；该条件不能排除弱天空信号，尚无无遮挡户外验收。不再重复相同UTC/收星测试，继续相机工作。')
(repo/'NEXT-SESSION.md').write_text(text)
(here/'README.md').write_text('''# 210：常态前摄接入（进行中）

已备份全部36份当前内核源改动、配置、符号表、模块顺序、Image及DTB。源码基线与手机204部署设备树均有910个节点；使用DTC YAML明确标记的引用单元归一化phandle后，没有剩余语义差异。普通整数单元未被当作引用改写。[备份核对](source-baseline-validation.json)、[语义比较](baseline-semantic-validation.json)

下一步把200已经取得实体RAW画面的IMX471接入正常板级DTS及模块配置。当前尚未部署210产物或重启；手机保持207第二boot、Image183及boot204。四路PLDO输入未知，不虚构供电父节点。

用户已答复GNSS测试条件是室内窗边；弱信号尚不能排除，没有户外验收。209的1000→418ms UTC误差输入对照无改善，候选未部署，不重复相同实验。[209报告](../kernel209/README.md)、[相关机型研究](../kernel205/GNSS-RELATED-DEVICES.md)。真实定位、相机其它镜头、蜂窝、蓝牙、传感器及完整打包仍在完整目标内。
''')
print('210 work-in-progress checkpoint and authoritative indoor-window condition recorded.')
