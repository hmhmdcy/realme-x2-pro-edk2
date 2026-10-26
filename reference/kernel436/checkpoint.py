from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['hardware','source','patch-replay','profile-export']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed']
archive=ROOT/'archive/NEXT-SESSION-through435-2026-10-22.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：436（恢复原厂 BLS，主摄完整 tone 实拍和 AF 通过）

完整多摄/ISP目标active。先读WORKING-BOUNDARIES、reference/kernel436/README。436保存同SOF FULL/真实PD10/实际6008B IPE包/成片，固定输入硬件回放两次原厂输出相同且等于实时成片；LTM off不能消除上游径向分布，LSC off对照减弱。定位到324内部图案用的BLS0/normalization1实验配置被继承进435。恢复本机Sunny GW1原厂IFE BLS后，大面积暗心/亮环/雾感明显减轻，LSC/GTM/TMC/LTM均保留。

## 当前候选与证据

用户候选 /mnt/samurai-full282/libcamera436-tone-domain/src/libcamera-v0.7.2，build1/IPA5。libcamera50923736B/af3bc105448c2d04407362992aa1682b6504956ded26a57d568544470f799c51；IPA8100224B/510529147d0489b58b62945e9a135ab031cb7cb2853f60589b5d5bd98af4f60c；proxy1674864B/093df5faa73b42b741e2b61d862fefc292fcf7ced2ccfb6f6f9389f70b182dcf。IPA/签名/proxy与435逐字相同。只增加可选只读同帧保存，0048补丁两文件以435为base，零fuzz/offset逐字重放。

内核未改，source354 HEAD9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3/samurai-vfe175-gtm-reopen434。434 CAMSS3edb28d1…/core d391fa24…/m2m e6828a0c…；正式仍420/419、Image363/DT389，未永久安装。

436原厂BLS：复用324 Sunny原件59238df7…，有界类型解码+原厂ParameterParser独立XML，两IFE根Default/Sensor.9共10区域全960U14/四阈值0，BPS990未混用。转换U16减量3840、Q11归一化2175/2048，只恢复这两项；原LSC/GTM/TMC/LTM/Gamma/色彩/PD10字段不变。私有factory-s5kgw1 profile b4b6daa2d8039963a9c07a6a09b27e87a293a0b102644a1f0ca3e89648f4c40b。export-profile.py是当前导出，stage-runtime默认修正配置；复现旧r1/r3要--uncorrected-baseline。原准备/parser脚本有一次性目录前置，不盲重放。

r1原配置24帧/21math；r2固定输入5回放（stock/noLTM/colour/bypass/stock）；r3只LSC关闭24/21；r4恢复BLS并保留所有原模块24/21；r5同修正配置+已有424 AF采集器205/202，Focused。总277实拍/265math+12bootstrap、另5回放。修正配置合计229帧/223math+6bootstrap；硬件恢复全部passed，newfaults0/taint0，全部worker/client终态。

逐帧审计核对 actual GTM cookie/generation→immutable TMC→同SOF FULL/PD10→IPE最终成功math history，上一lux来自成功历史。r1/r4/r5 SOF12 token13/revision10，GTM5/gen5来源stats9；r3SOF12 token9/rev3，GTM3来源stats3，允许未消费PD10与SOF间隔。各流两个GTM bank。bootstrap不冒算math。IPE库/IPA5/proxy必须匹配；435入口锁与同步frameProcessed、PD10占有/顺序和控制等ACK不阻断统计的修复不变。

## 尚未验收与下一步

205帧AWB全程locked0；AF期间前景变化，不能把FoM变化全当作镜头改善。末帧可辨物体且颜色显著改善，但仍不算绝对色准/平场/噪声/清晰度验收。下一步先查AWB稳态、统计/有效增益/触发语义与残余偏色，继续原厂数据及实拍；随后其它摄像头、尺寸/视频、完整legacy/manual/v2/HDR tone。第五2MP、个体光学、多摄几何同步等363完整范围保持。

435完整自动tone链路和数学检查继承，支持TMC11 model2，原manual/v2 flags1与非零GTM份额保留；不是所有OEM分支完整移植。DC仍RT2→kind0→bank0，coarse DC写/clear、FULL IP读；430/431原厂遍次和因果消费证据沿用，未逐字节导出SRAM。a7scratch不是统计，429越界诊断禁止恢复/不猜MMIO。

## 工作环境

每次WSL source/build/ext4先root调用284/storage.py mounted_build原32GiB E盘，禁止格式化重建；SDK临时bind，用完卸载。436 host继承429新guard，USB SSH正常，私有原件/系数/全日志/像素仅E:/edk2-samurai-out/kernel436。2026-10-22清理旧中间对象约9.5GiB+Windows uv缓存，C可用约11.8GiB，WSL已恢复读写。镜像仓库实际HEAD在436开始时为efd01b4c且435对象缺失，不能信此前d21fac6a记忆；保留所有无关修改，通过public_module恢复435和436并scoped本地提交，不push。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP目标。436已找到并修复主摄大面积雾感/亮环的重要配置遗漏：324内部图案BLS0被继承进435实拍。原Sunny GW1两个IFE BLS根10区由有界解码+原厂parser交叉一致，恢复3840 U16减量+2175/2048 normalization；LSC/GTM/TMC/LTM全部保留。固定同SOF FULL/PD10/6008包回放stock重复逐字同且等于实拍，LTMoff仍有上游径向分布、LSCoff减弱。修正r4 24帧21math+r5 AF205帧202math，Focused；正式环境恢复无fault taint0，未永久安装。当前用户候选libcamera436-tone-domain build1/IPA5，lib af3bc105/IPA51052914/proxy093df5fa；IPA数学签名proxy同435，kernel仍434 HEAD9bc07e63。AWB205帧全locked0、AF期间前景变化，颜色/光学质量未验收。下一步AWB稳态/统计有效增益/原厂触发语义和剩余偏色，再其它相机模式视频及363完整范围，不缩小目标。读436README/NEXT/WORKING-BOUNDARIES。export-profile.py/staging默认修正profile，旧实验须显式uncorrected；原件私存，284挂原盘，429guard，不猜MMIO。\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/rel;d=json.loads(p.read_text());d.update(stage=436,latest_work_stage=436,latest_work_phone_accessed=True,last_live_hardware_evidence_stage=436,last_successful_scene_stage=436,last_successful_automatic_ipe_scene_stage=436,
 maintained_userspace_ipa_candidate_stage=436,maintained_userspace_ipa_candidate_build=1,ipe_auto_tone_latest_evidence=prefix+'reference/kernel436/README.md',ipe_auto_dual_pass_evidence=prefix+'reference/kernel436/hardware-validation.json',
 ipe_factory_main_bls_restored=True,ipe_factory_main_bls_evidence=prefix+'reference/kernel436/profile-export-validation.json',ipe_main_large_radial_artifact_reduced=True,ipe_main_awb_locked=False,
 ipe_main_image_quality_accepted=False,ipe_main_image_quality_issues=['AWB not locked in205-frame AF run','absolute colour/flat-field/sharpness/noise not accepted'],ipe_full_factory_tone_pipeline_complete=False,in_progress_installed=False,
 latest436_live_images=277,latest436_math_commits=265,latest436_fixed_input_replay_jobs=5,latest436_corrected_profile_images=229,latest436_corrected_profile_math_commits=223,
 current_device_health='436 r1-r5 complete;formal modules/services/resources restored,no newfault,taint0;main BLS correction and AF verified,AWB/absolute quality pending',current_device_last_successfully_restored_experiment='436 r5 corrected original BLS with205-frame main AF and202 automatic tone math commits')
 p.write_text(json.dumps(d,indent=2)+'\n')
note='436当前：恢复主摄原厂BLS，LSC及GTM/TMC/LTM保留，大面积雾感/环状亮度明显减轻；修正配置229实拍/223数学提交，其中AF205帧并Focused。AWB未locked，绝对画质与其它摄像头范围继续。正式环境恢复，无fault/taint0，未永久安装。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel436/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel436/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel436/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('435当前：');p.write_text(note+'[436证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';t=p.read_text();assert '[435 主摄原厂GTM自动链路与成功历史](reference/kernel435/README.md)' in t
p.write_text(t.replace('[435 主摄原厂GTM自动链路与成功历史](reference/kernel435/README.md)','[436 原厂BLS修正与主摄自动tone实拍](reference/kernel436/README.md)'))
print(json.dumps(dict(stage=436,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
