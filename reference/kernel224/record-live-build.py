from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel224')
state=json.loads((private/'r9-build-state-private.json').read_text());pid=state.get('pid');live=pid is not None and Path('/proc',str(pid)).exists()
assert live and not state.get('terminal',False),'Use terminal checkpoint, not a live-build note'
snapshot=Path(state['snapshot']);assert snapshot.exists()
p=repo/'archive/NEXT-SESSION-through223-2026-10-16.md';assert not p.exists();p.write_bytes((repo/'NEXT-SESSION.md').read_bytes())
s=(repo/'NEXT-SESSION.md').read_text();a=s.index('2026-10-16，');b=s.index('\n\n',a)
s=s[:a]+'2026-10-16，224进行中：手机仍223 fae1/r8-r3，RAW统计r9构建89779存活，原214保护在private/libcamera214-before224，终态须恢复。私人capsule kernel224/current-work-private.json；全goal active。[224记录](reference/kernel224/README.md)、[边界](WORKING-BOUNDARIES.md)。'+s[b:]
s=s.replace('运输reference/kernel223/host.py','运输reference/kernel224/host.py').replace('guard /var/lib/samurai/k223-baseline/boot-id-private.txt','guard /var/lib/samurai/k224-baseline/boot-id-private.txt')
s=s.replace('原/work/libcamera2254文件/链接/权限已恢复，无待恢复快照；候选/work/libcamera223-built，r7缓存220-built保留。','原214的2254文件/链接/权限已保护；224构建89779存活，原树在private/libcamera214-before224，勿挪活编译树；候选r8保留223-built。')
s=s.replace('rootfs132整合按[清单]','rootfs132整合按[清单]')
assert len(s.encode())<=6500,len(s.encode());(repo/'NEXT-SESSION.md').write_text(s)
note='''# 224：RAW独立取流的统计与曝光元数据

当前手机仍boot219/Image183/e49/CAMSS fae1/libcamera r8/config-r3。本轮重新认证并取得16帧RAW基线，曝光/增益元数据均缺失（探针以−1表示缺失，不是硬件负值）。[基线](baseline-raw-gap-validation.json)。

候选0015在CPU RAW-only路径中只读采样原缓冲，不分配RGB输出，启用原软件IPA的配置/启动/请求/统计/元数据流程；保留223捕获序号快照，输入失败时不等待缺失元数据。非CPU旧RAW路径保持。[补丁](libcamera-raw-only-statistics.patch)、[源指纹](candidate-source-validation.json)。

r9/r4完整构建正在89779运行，保留原14补丁和全部子包。SDK原214树在private/libcamera214-before224，构建活跃时不能移动；终态需恢复并核对2254个文件/链接/模式。手机仍r8，候选未验收/部署。

标准手动曝光/独立Auto-Manual还未加入。GNSS真实fix、后置四摄、蓝牙/传感器/蜂窝等全外设目标保持active，关灯/室内窗边、不存图和不外部照明的条件保持。
'''
(here/'README.md').write_text(note)
p=private/'current-work-private.json';d=json.loads(p.read_text());d.update(state='RAW baseline confirms absent exposure/gain metadata; r9 complete-feature build live, original214 protected',active_build_session=89779,guard='/var/lib/samurai/k224-baseline/boot-id-private.txt',build_state_file=str(private/'r9-build-state-private.json'),protected_original214_snapshot=str(snapshot));p.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(stage=224,live_build_confirmed=True,original214_snapshot_exists=True,next_session_bytes=len(s.encode()))))
