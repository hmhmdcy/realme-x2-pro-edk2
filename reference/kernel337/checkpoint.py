from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
assert json.loads((HERE/'bayer-luma-validation.json').read_text())['passed']
state=dict(stage=337,source=str(HERE/'libipa'),changed_sources=['libipa/aec_bayer_luma.h','libipa/aec_bayer_luma.cpp','libipa/aec_lux.h','libipa/aec_lux.cpp'],generic_bayer_luma_and_lux_oem_instruction_verified=True,
 candidate_ipa_source='/home/cy122/x2pro-linux/libcamera214-root/work/libcamera335-ccm-built/src/libcamera-v0.7.2',ipa_integrated=False,current_camera_grid=[32,24],required_grid_axis_multiple=16,
 actual_hardware_statistics_verified=False,physical_exposure_table_mode_binding_verified=False,kernel_board_sensor_changes=False,phone_changed=False,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/relative;d=json.loads(p.read_text());d.update(current_camera_evidence=prefix+'reference/kernel337/README.md',in_progress_stage=337,in_progress_evidence=prefix+'reference/kernel337/README.md',in_progress_installed=False,
  aec_bayer_luma_oem_instruction_verified=True,aec_bayer_luma_evidence=prefix+'reference/kernel337/bayer-luma-validation.json',aec_lux_runtime_integrated=False,aec_lux_actual_hardware_statistics_verified=False,aec_current_grid_compatible=False)
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：336','# 当前检查点：337').replace('reference/kernel336/host.py提供raw_ssh。','reference/kernel337/host.py提供raw_ssh。')
start=s.index('下一步337从335 IPA候选+334内核源继续');end=s.index('当前没有活动构建/采集session',start)
s=s[:start]+'''337已恢复普通RGB Bayer→16x16 processed-luma→lux数值链，generic libipa/aec_bayer_luma.{h,cpp}+更新版aec_lux.{h,cpp}在reference/kernel337/libipa，未进IPA/内核。原AEC函数4e5d0..4ed60 ProcessBGStatsRegion完整；父3c958..4198c ProcessFrameStats中权重3cedc..3cff4和无效增益log路径3d7b8..3d818、pool accumulate3d608..3d650/normalize3d68c..3d744片段，最后336完整CLux包装。起初权重oracle从3cee4少了x27加载，第一12期望字节错，已从3cedc真实加载开始修正；generic实现没有为错oracle改算法。主机/ARM各1523records29636bytes0diff，267weights(89factoryprefix*3)、1248单region、8grid额外9728原regioncalls，默认FMA/Werror。

337普通RGB/no explicit sat: sums/count orderR,B,GR,GB；每通道totalSum=rawSum+(N-count)*highThreshold；green integerfloor((grTotal+gbTotal)/2)后float；weighted=B*wB+(R*wR+G*wG)，scale=1/2^(inputbits-8)，Y=scale*weighted/(explicitNormalization*N)。satFrac=sumMissing/(4*N)。权重optionalcomp=curGain*tuningWeight/refGain，不再归一化；无效gains回退base。适用stride1/全部validcells，HDR/Y/explicitSat/skip2或4等未移植。当前driver确是RGB/shift0/noSatExt/input14，源camss-vfe-175-stats.c，maxregion390x512/count16bit/30bitsums。

337关键发现：原普通ProcessBGStats入口3cdac..3ce24强制columns&15=0、rows&15=0且总<=3072，当前CAMSS32x24不兼容。pool按integer块columns/16、rows/16分组逐region累加、最后除count；16x16/32x16/32x32/64x48都与原指令一致。物理ABImax768，不需扩大容量就可32x16；不能把当前32x24直接全局平均说成原厂等价。父x26=PARENT、ProcessBG对象PROC=PARENT+128，Y记录PROC+0x30a8+24*i；legacy pool在PARENT+0x15120=PROC+0x150a0，与GetLegacyYRegionStats的子对象偏移匹配。stock_bg.py严格允许片段/普通region，pool整条原指令对generic结果，log/math沿336stub。

337还纠正336人工亮度上限：补偿权重可使8bit缩放Y>255，原lux包装不cap；337平均函数只拒负/nonfinite，补偿grid实际Y约845~863也精确。后续必须拿337新aec_lux源，不只336旧cell<=255版本。没有phone操作，仍335恢复的r26/r21+298/305/318/325与PW/WP19667/19708；不重测旧全量。

下一步338优先从334 SoC CAMSS统计源（camera334-ccm-kernel clean commit6c762e...）让BG网格满足16倍数，保持现有UAPI最大容量/可变rows元数据，32x16可在原768预算内。实际内核/内部TPG统计验证后，把337数值链接335IPA，再曝光表物理模式/供应商绑定和lux→LSC/CCM动态调校/统一发布。底层改动应在CAMSS统计后端收敛，不改板级DT或传感器。正常光照光学、几何同步、连续AF等完整范围仍在。''' +s[end:]
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISPgoal active。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel337/README.md。337普通RGB Bayer→16x16 luma→原lux链主机/ARM1523records零差，未进IPA。关键：当前32x24不符合原厂横纵16倍数约束；下一步338从334 CAMSS stats后端实现兼容网格(32x16在原768容量内)、真实TPG统计验证，再337原语→335IPA/物理曝光表模式绑定/lux动态LSC和CCM。补偿亮度可>255，337已去掉336旧函数人工上限，用337/libipa全部4文件。候选335core+334kernel仍未安装，phone未操作、PW/WP19667/19708、安装r26/r21+298/305/318/325。用户关灯继续，复用不变证据。\n')
p=ROOT/'linux-port/camera/README.md';s=p.read_text();banner='337当前：普通Bayer统计到原厂16×16亮度/lux路径在主机与ARM各1523组一致；发现32×24网格不兼容，下一步底层统计网格适配。尚未接入实时IPA或更改手机。[337亮度链](../../reference/kernel337/README.md)。以下为历史记录。\n\n'
if not s.startswith('337当前：'):p.write_text(banner+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded337 Bayer-luma oracle and the real32x24 geometry incompatibility; hardware grid next.')
