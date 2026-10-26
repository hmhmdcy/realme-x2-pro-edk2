from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['build','exposure-domain','ipa','profile','packet','coarse-gap','hardware','scenes','source']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
r=json.loads((HERE/'runtime-r1-validation.json').read_text());assert r['terminal'] and r['passed'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
archive=ROOT/'archive/NEXT-SESSION-through423-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
text='''# 当前检查点：424（修正LTM衰减坐标与统计缺失恢复；主摄AF＋自动曲线实拍通过）

完整多摄／骁龙ISP目标active，未完成。先读WORKING-BOUNDARIES与reference/kernel424/README。上一轮423是progress：真实主摄单曝光TMC/LTM闭环与144帧实拍；本轮继续实际源码／设备工作，不重跑旧大矩阵或手机事务。423交接归档archive/NEXT-SESSION-through423-2026-10-21.md。

## 424修复与证据

发现423衰减坐标错误：原厂LTM的IFE父节点0x10000用请求+2892 luxIndex更新current/prev，而423用了曝光×增益推算的exposureIndex。实际原HAL0x35fe8c..0x35ffbc八组绑定／暖机检查确认，无provider。新IpeToneProfile曲线用frame.luxIndex，IpeToneState保存ltmLuxValid/ltmLuxIndex，仍仅最终图像+RAW成功回执提交；首次有效计算previous=current。Android最大流水线延迟/BET暖机另有规则，未冒充已映射Linux同语义。

实际编译profile对象验证：固定lux仅改物理曝光坐标输出不变；重现旧域反例改变123字节；只改已确认lux历史时LTM改变120字节。实际原厂样例TMC同时gtmEnabled1且非零gtmFraction，不能说GTM未应用自然无影响。

prepareIpeParameters已有观测无有效lux/BG时持有committedTone，不推进数学历史；无历史则已有旁路。恢复后从最后成功state计算。保留token/epoch/size/真正计算错误检查。实际ARM64 IPA四模式检查首次缺BG、提交后缺BG、恢复、失败/忙/旧回执/restart通过；原423真实模块同夹具首帧返回-ENODATA，反例保留。缺BG是合法BHIST-only测试，未放宽解析器／未手机注入故障。三包通过当前native kernel validator。

候选/mnt/samurai-full282/libcamera424-tone-domains/src/libcamera-v0.7.2，来源423。仅3个生产文件变，0045补丁从423零fuzz复现。私有IPA仍3，kernelUAPI1/6008B。build-r1 64.12s，源码前后hash一致且实际camss.cpp与ipe_tone_profile.cpp对象重编。core SHA14b6842a4d4005d0a2b72a8065d4fe00d5bdee7ea2fae5c68b785857d12b25b8、proxy8cc147afe57aeaea21f3359f1c7eb935d401ebeb2e1ed091cf8e150438ba45d5与423相同；IPA324a821f1c72f0ebb983d73f33a4500c4d696640932c362e0020e10958088129，新签名已验。未永久安装，正式仍420 r31/r26+419生产驱动。

## 实拍／设备

新capture在AE预热24帧后用标准AfTrigger实际扫描，等待Focused/Failed终态再16帧，期限20s；帧数随扫描决定。主摄4608×3456→640×480 NV12／testPattern0，普通及隔离IPA各205帧、161份Scanning，最终都Focused。数值提交202/200共402，逐项同SOF观测摘要→6008B queue→最终成功回执，并核对previous-ltm-lux=上一提交lux；独立摘要56/59。持有3/5次不推进历史。没有应用滤镜。

按元数据选择预热最后帧与最终帧，普通FoM1005→1633，隔离810→1598；中央归一化梯度0.000565→0.001267、0.000489→0.001211。已查看AF前后原始解码图，中心细节提升但仍有雾感／偏色；这不是绝对MTF/色准/噪声／全景焦面验收。样本私存在/mnt/e/edk2-samurai-out/kernel424；手机/var/lib/samurai/k424-tone-r1保留205帧/组，host收final和warmup样本。

410个IPE作业全部direct成功，新增内核fault0/dump0/取消0/failed0/first_error0；最终jobs=completed=direct793，starts/stops25。users/running/fatal/pinned/orphans0，core电源/时钟所有权/IRQ/映射/DMA/导入释放，PW/WP各恢复一个，owner_refs53桌面CAMSS，历史taint512不清。worker/client/collector终态，无活动build/SDK bind。正式419模块、Image363/DT389/CAMSS389/FW/SGowner以及原厂文件不改。

## 已确认下一实际缺口（不要回避为更多固定调色）

当前单full-pass kernel编码器固定passes1、仅全尺寸输入/输出。用当前实际kernel函数、主摄实际LTM/colour/gamma程序、完整原固件prepare，640和650×480双核分别DC0/1：striping/32B job/整512KiB CDM完全相同。data_collection标志不创建粗级pass；完整DC尚未实现。probe首轮仅ctypes自动NUL造成tail多比1字节，修精确capacity后过，无native code改动。勿将flag1/普通像素变了/无关scratch当DC统计已验证。

下一步优先恢复原厂粗级遍次、维度/裁剪及缓冲绑定，再验证粗级数据产生和full-pass IP消费。原HAL保留符号：LTMDCStripeConfiguraion0x1556a0，generateLTMDCmode0x155770，generateLTMDCoutW0x1557a8/outH0x1557b8；原完整striping/FW oracle来自404/406可复用。现有current kernel/完整HAL两组命令对照私存424/coarse-width-*。这是具体已证缺口，非阻塞用户输入。

GTM是IFE/BPS路径，固定CamxChi源码64个18bit base/26bit slope/64bit DMI，只是reference非本机已验。实际IFEGTM10::Execute0x31fc00、IQInterface::GTM10CalculateSetting0x37c818已定位，尚未执行/适配。需从既有OEM文件提取真正GTM树/本机数学，并把GTM/ADRC版本关联到实际IFE parameterHistory和对应图像IPE，遵守stats→未来IFE生效→同图像IPE的因果顺序，不能用当前图像hist声称已改同帧上游GTM，不能清零gtmFraction伪造完整。

423单曝光unityDRC/HDR/LEDoff/no-face策略仍明确，不是Android两槽/rawAEC124/140。前摄原厂TMC关闭保持，其他摄像头／视频模式tone未扩展，主摄2592调校导出未硬测。后续扩多摄、配套包部署、连续/清晰场景画质。完整scope见reference/kernel363/REMAINING-CAMERA-SCOPE.md：第五2MP身份/mux不猜OV02A10、多模式帧长防频闪、连续AF、几何/多摄同步等保持。

每次WSL source/build/ext4访问先root storage284.mounted_build挂原32GiB镜像，不重建格式化；Unicorn PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。先确认build进程terminal才改输入源码/部署，避免423早期残留对象。原厂系数/ELF/ASM/完整日志/图像私存，公共仅作者代码/脱敏摘要，本地scoped mirror提交护无关index，不push。保护NV/OTP/备份/密钥/电池温控。
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从424继续完整多摄ISP目标。先读NEXT和424README。已修LTM用lux衰减历史、缺BG/lux持有已提交曲线；实际IPA和旧错误反例/内核包验证通过，主摄普通+隔离各205现场帧、402数值提交及2次真实AF Focused、细节提升，仍雾感偏色非画质完成。当前793direct/failed取消0、25starts/stops、服务恢复/资源释放，正式r31/r26+419不变，候选IPA3未安装。已用当前kernel+完整原FW证明DC0/1对单full-pass的整CDM无变化，完整DC未实现；直接恢复粗级遍次/缓冲/数据产出与IP消费，不绕成更多固定调色或把flag当统计。GTM实际入口和非零份额已确认，须补本机树/算法及IFE参数版本→同图像IPE的因果绑定；单曝光unity策略非完整Android。原件均可复用，不重跑旧矩阵/旧事务。其余镜头/视频/第五2MP身份mux和完整scope保持。WSL先storage284，构建terminal后改源，私表图像不导出，本地提交不push。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 d.update(stage=424,latest_work_stage=424,current_device_revalidated_stage=424,in_progress_installed=False,
  ipe_ltm_lux_attenuation_candidate_corrected=True,ipe_ltm_lux_attenuation_candidate_hardware_verified=True,
  ipe_missing_lux_reuses_committed_program=True,ipe_auto_tone_main_af_scene_verified=True,
  ipe_auto_tone_latest_evidence=prefix+'reference/kernel424/README.md',
  ipe_full_factory_tone_pipeline_complete=False,ipe_ltm_full_dc_coarse_pass_implemented=False,
  ipe_ltm_single_pass_dc_flag_no_native_command_effect_verified=True)
 p.write_text(json.dumps(d,indent=2)+'\n')
note='424当前：修正LTM衰减为同SOF lux历史，补缺BG/lux持有已确认曲线；主摄普通／隔离各205帧和实际AF成功，共402次数值提交。已证明当前单遍DC标志不产生粗级命令，完整GTM／DC及多摄画质仍未完成；候选未安装，正式r31/r26+419保持。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel424/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel424/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel424/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('423当前：');p.write_text(note+'[424证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();needle='[423 主摄自动TMC／LTM与实拍](reference/kernel423/README.md)';assert needle in s;p.write_text(s.replace(needle,'[424 LTM输入域修正、恢复与AF实拍](reference/kernel424/README.md)'))
print(json.dumps(dict(stage=424,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
