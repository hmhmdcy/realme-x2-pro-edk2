from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert not build['exit_code'] and not build['diagnostics']
for name in ['register-validation.json','pattern-r2-capture-validation.json','pattern-r2-image-validation.json','final-state-validation.json']:
 assert json.loads((HERE/name).read_text())['passed'],name
source=json.loads((HERE/'source-state.json').read_text());assert source['tracked_clean'] and source['temporary_hardware_tested']
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel334/README.md',in_progress_stage=334,in_progress_evidence=prefix+'reference/kernel334/README.md',in_progress_installed=False,
  ccm_supported_by_deployed_camss_backend=False,ccm_candidate_backend_hardware_verified=True,ccm_candidate_backend_evidence=prefix+'reference/kernel334/pattern-r2-image-validation.json',
  ccm_candidate_kernel_source=source['source'],ccm_candidate_kernel_commit=source['commit'],colour_temperature_ccm_linked=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：333','# 当前检查点：334').replace('reference/kernel333/host.py提供raw_ssh。','reference/kernel334/host.py提供raw_ssh。')
s=s.replace('332后PW/WP pid16618/16621、uid10000。','334后PW/WP pid18338/18365、uid10000。')
start=s.index('下一步334从325内核源clean提交')
end=s.index('继续动态AEC/CCT触发',start)
s=s[:start]+'''334：VFE175 CCM SoC后端已实现/临时实机验证，未安装。源码/home/cy122/x2pro-linux/camera334-ccm-kernel，samurai-ccm334，commit6c762eae4a4af55d8d9111d3c9fd8c2880f5dad1，parent325 4318dd1c2...，tracked clean。6文件133insertions/3deletions，无板级DT/传感器改动。ccm.c/h独立后端、pixel挂validator/apply/init/stop、17x params容量改COLOR_MAX，UAPI新增容量宏且只更新offset注释。header/enum/结构ABI不变，完整WB+BHIST+LSC+CCM envelope1888bytes。寄存器RMW保留其他位，coeff12s/K11s、GBR左右复制、0x48bit1、0x760/784/790，停流关闭、重开流单位但disabled。

334实际驱动函数主机/AArch64 Werror各2866参数对原寄存器位域，全MMIO/保留位、header-only disable保护页、非法flags/字段/padding、enable状态/生命周期全过。W=1 KCFLAGS=-Werror CAMSS及现有依赖闭包构建35.37秒无诊断/共享build恢复，module private334/qcom-camss-ccm334-r1.ko，SHA4f7ef0cadbec5e0dbd3df5b51d179402674e782fc7c8808ec09ce4f76dd63853，noteSHA43cc882ad8d744122dde70555e6f67784517c2acbee00a3fb1c2ece843f2d533。

334 R1 worker17856在私有factory文件校验处0帧返回2，错误是生成文件ENABLE写成DISABLE（V4L2宏ENABLE=2/DISABLE=1），驱动未错；模块/服务恢复，fault0/taint0。只修正payload，--payload-only复用工具/内核，R2 worker18160完成8阶段31帧/8图及四摄Gst各12帧（共79），无总线/相关故障。主摄ShadeColorBars2，disabled/unityQ7/非对称交换+G*.75/unityQ10/offset RGB[128,-64,32]/disable/factory/disable；两Q unity和disable回到基线逐字节相同，三个变化阶段均真图像效果。factory明确Qtech Default37 DRC1/HDRsens1/LED0/lux100/K6500诊断，未供应商绑定。

334近似NV12模型通道混合mean.381/p991.216；offset14-bit归一化mean.261/p99.927为候选域最佳，支持14bit解释。factory mean.692/p995.445/max14.093，预测输出远离截断p993.265；这不是精确RAW/光学校准，不隐藏误差或声称所有像素吻合。kernel334/pattern-r2-image-validation.json，图像/私有matrix/capture日志留private334/pattern-r2，不镜像。kernel334/samurai-ccm.c与prepare-probe.py使用实际kernel UAPI交叉gcc，无需另装工具链。普通工具plane sentinel保留但已移除任意90%像素变化门槛，按确认参数后的稳定图结束。

334 R1/R2所有worker终态，R2恢复原模块note与实验前相同；媒体/controls/服务恢复、CAMSS/CCI suspended、九rails disabled/users0，taint0，PW/WP18338/18365 uid10000。设备仍r26/config-r21+298/305/318/325，模块文件/包/Image/DT不变、未刷写/重启/写NV/OTP/persist/EEPROM。334候选尚未与332 IPA联动；不把临时kernel通过说成默认CCM已部署。

下一步335从332候选libcamera332-cct-built加入333通用CCM数学、显式ColourCorrectionMatrix控制/手动CCT或增益/自动WB CCT矩阵选择，参数revision和SOF历史应报告有效量化矩阵；kernel334已具备后端，需临时搭配。旧默认/无CCM配置保留无新块。进一步动态LSC/lux、真实normal光学和供应商/多摄几何同步等完整范围继续。发布新包/模块时从332/334源，不用旧321/318生成器覆盖新改动。

'''+s[end:];p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel334/README.md。333原厂CCM28根567区/通用数学已过，334新增VFE175后端主机ARM位域2866组、Werror模块、真实8阶段矩阵图+四摄Gst通过；临时模块已恢复，未安装。334源camera334-ccm-kernel commit6c762eae4a4af55d8d9111d3c9fd8c2880f5dad1 clean；332 IPA个体CCT候选继续作为335基线，下一步显式矩阵/CCT/AWB→CCM和有效SOF矩阵元数据。1888byte容量、12s系数11s偏移、ENABLE2/DISABLE1，勿重复R1 payload错flag。当前安装仍r26/config-r21+325/318/305/298，全部worker终态，PW/WP18338/18365。用户关灯继续，不重读EEPROM或旧全量回归。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='334当前：VFE175颜色矩阵后端通过Werror、主机/ARM寄存器测试和实机8阶段/四摄Gst验证；临时模块已恢复，尚未安装或联动332 CCT。下一步IPA矩阵控制和色温联动。[334硬件支持](../../reference/kernel334/README.md)。以下为历史记录。\n\n'
if not s.startswith('334当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded334 real VFE175 CCM support; temporary module restored, IPA integration next, goal active.')
