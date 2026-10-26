from pathlib import Path
import hashlib,json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel195';old=(root/'NEXT-SESSION.md').read_bytes();s=old.decode();assert '阶段194' in s
a=s.index('最后核对：');b=s.index('\n\n## 当前部署',a)
s=s[:a]+'''最后核对：2026-10-15，阶段195，完整外设goal active。PM8008地址迁移失败后重新请求自身复位，37场景通过且旧版失败；新模块cold/warm真机probe保持。可撤销VIO phandle已让标准OF精确查到真实1.8V，撤销后节点/电源状态恢复。IMX471尚未实体probe或取帧。193实体ID0x0471、r2时钟WARN/taint512保留；规则见[边界](WORKING-BOUNDARIES.md)，用户暂无耳机。'''+s[b:]
s=s.replace('| 相机194 | Q GPIO4复位后8/9、SID2；新MFD自身设置SID1迁移4/5并绑定/注册七LDO；warm直接probe。前中后全部采样一致，临时节点/模块撤销，P0/Q1恢复 |','| 相机195 | 新MFD cold/warm各通过，七LDO采样与P0/Q1恢复；VIO精确OF lookup1.8V、未enable/设压，节点/对象/状态恢复，临时模块撤销 |')
s=s.replace('最新15014.14秒','最新16368.69秒')
s=s.replace('依据：[194报告](reference/kernel194/README.md)、[MFD原生](reference/kernel194/pmic-native-validation.json)、[最终健康](reference/kernel194/native-health-validation.json)、[193实体ID](reference/kernel193/README.md)。[193逐字快照](archive/NEXT-SESSION-through193-2026-10-15.md)','依据：[195报告](reference/kernel195/README.md)、[MFD原生](reference/kernel195/pmic-native-validation.json)、[VIO引用](reference/kernel195/vio-native-validation.json)、[最终健康](reference/kernel195/native-health-validation.json)。[194逐字快照](archive/NEXT-SESSION-through194-2026-10-15.md)')
s=s.replace('新增Sony绑定与3个OF开发C文件','新增Sony绑定与4个OF开发C文件').replace('194开发代码/两绑定分开checkpatch通过，完整集合有3项“绑定应分开”提示。[最终源/补丁](reference/kernel194/source-final-validation.json)','195开发代码/增量补丁checkpatch通过，绑定沿194。[当前源/补丁](reference/kernel195/source-final-validation.json)')
s=s.replace('MFD源0101c9b5…/模块9382ba34…；fixture e5b9405e…。','MFD源057ccd62…/模块d1ff82c0…；PMIC fixture e5b9405e…，VIO helper源868c9b2a…/模块9e83668e…。')
s=s.replace('7+35实际C函数场景ASan/UBSan通过；','194电源7场景/195地址37场景ASan/UBSan通过，旧地址函数被新增回归检出；')
s=s.replace('193独立前摄PM引用修复/失败保留。','VIO临时phandle301标准OF lookup通过并撤销；正式DT由编译建立引用。193独立前摄PM引用修复/失败保留。')
s=s.replace('194基线另存；host194沿用','195基线另存；host195沿用')
s=s.replace('- 194归档0afa8fa2…/42、193 936fe956…/67、192 322bfbce…/23均逐成员验证；191主843c4d47…/42及radio b6628078…/23保留。','- 195归档10c5f4aa…/37、194 0afa8fa2…/42、193 936fe956…/67均逐成员验证；192/191原件索引保留在快照。')
a=s.index('1. 正式IMX471');b=s.index('\n2.',a)
s=s[:a]+'''1. 组合VIO live phandle、Q LDO约束、pinctrl与CCI，让普通IMX471实体probe/PM，再接CAMSS取帧。当前驱动仅4lane/200MHz/1928×1088 RAW10；[同平台Hotdog仓库](https://github.com/Sr-0w/hotdog-linux-bringup)固定47087509c4289c2580c54f5433e55366b2e00445、WSL /home/cy122/x2pro-linux/hotdog-ref195无checkout。其1748方形/525.2625MHz和CAMNOC补丁已保存私人供比较；PM8009/BOB/gate/CCI1 master0/弹出机构不照搬。主线评审已删除sensor重复PD，先实测正常CCI父层次。前摄193 ID确认，其它BIN仍仅候选。'''+s[b:]
s=s.replace('Q安全拒绝且自身保持复位，双PMIC顺序仍待设计。','Q安全拒绝且自身保持复位；释放后的迁移错误也请求自身复位，复位调用本身失败只记错、不保证物理恢复。双PMIC顺序仍待设计。')
assert len(s.encode())<=6500,len(s.encode());archive=root/'archive/NEXT-SESSION-through194-2026-10-15.md';assert not archive.exists();archive.write_bytes(old);(root/'NEXT-SESSION.md').write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';lines=p.read_text().splitlines();lines[2]='用途：当前硬件验收清单。最后核对：2026-10-15，阶段195。PM8008迁移失败复位回退37场景通过，新模块cold/warm真机probe保持；可撤销VIO精确OF查找1.8V通过，节点/电源状态恢复。IMX471尚未实体probe或出图，193 ID0x0471与时钟WARN/taint512保持。16368.69秒同189 boot，三个DSP/MM191/PowerState3/SensorProxy正常、临时模块已卸载；GNSS fix/蜂窝/BT等完整goal active。[195报告](../../reference/kernel195/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 193真实CCI ID0x0471/供电PM撤销通过；194/195普通MFD Q复位地址8→4及warm probe、七LDO注册/采样恢复；195失败复位回退37场景，VIO精确OF供电查找/撤销真机通过，IMX471 OF/三电源/pinctrl模块ABI通过 | 尚未实体sensor probe/出图；正常CCI父层次runtime PM与MIPI/CAMSS实测、四路PLDO输入/双PMIC冷启动、其它镜头/模式/用户态待验；候选PMIC schema仍4项缺失，193时钟WARN/taint512保留 |'
p.write_text('\n'.join(lines)+'\n');print(json.dumps(dict(stage=195,previous_checkpoint_archived_verbatim=True,previous_sha256=hashlib.sha256(old).hexdigest(),next_session_bytes=len(s.encode()))))
