from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['build','ipa','packet','domains','interpolation','built-caller','roundtrip','hardware','scenes','source']:
 assert json.loads((HERE/(name+'-validation.json')).read_text())['passed'],name
for attempt in ['r2','r3']:
 r=json.loads((HERE/('runtime-'+attempt+'-validation.json')).read_text());assert r['passed'] and r['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
archive=ROOT/'archive/NEXT-SESSION-through422-2026-10-21.md';assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
text='''# 当前检查点：423（主摄单曝光 TMC／LTM 自动闭环已实拍，候选未安装）

继续用户授权的原厂调校复用、多摄／骁龙 ISP 适配，尽量底层收敛。先读 WORKING-BOUNDARIES 与 reference/kernel423/README。完整多摄与原厂画质等价目标未完成。422交接归档 archive/NEXT-SESSION-through422-2026-10-21.md；不要重跑旧事务或大算法矩阵。

## 423真正完成

主摄同 SOF BHIST1024／实际曝光增益／lux／IFE Gamma → 原厂 AEC 插值／TMC11 → LTM13／IPE Gamma → 同帧6008B MediaRequest → 最终图像+RAW配对回执 → 数学历史。IpeToneProfile已实际引用11个公共数学cpp，非死链接。每摄像头一份未确认计算；忙时复用已提交程序不推进历史；失败不提交，stop清空，epoch／SOF／token／baseRevision拒旧结果。保留421统计先发布再同步IPA的重入修复。

候选 /mnt/samurai-full282/libcamera423-ipa-tone/src/libcamera-v0.7.2，私有IPA3，内核UAPI仍1／6008B。0044补丁7文件从422零fuzz复现。最终build-r3强制重编调用方119.55s；core SHA14b6842a4d4005d0a2b72a8065d4fe00d5bdee7ea2fae5c68b785857d12b25b8，IPA09aae3f1f2cf53db595f41f6c08f11ed03a2a30d4c2e57dba063e67942d37695，proxy8cc147afe57aeaea21f3359f1c7eb935d401ebeb2e1ed091cf8e150438ba45d5。实际ARM64 IPA失败／持有／成功／旧回执／重启验证及签名通过，3个真实生成参数包通过当前kernel validator。新LTM选择器30组21480B对原HAL零差，ASanUBSan。

主摄sunny S5KGW1的4608×3456／2592选定Preview原厂根已私有导出，硬件只测3456。明确single-exposure-linear-ae-no-face策略，DRC／HDR／dark split=1、LED关、无脸过渡、每次新计算force TMC；不是观察到的Android双槽／rawAEC124/140。前摄原厂TMC关闭，其他摄像头不擅自开启。原厂GTM enabled元数据保留，但没有新增或证明IFE GTM分支，不称完整OEM曝光分配等价。

## 处理域与实拍

实际IFE发布段只写64个green低10bit base，结构65项的第65项不写；实际LTM读65个unsigned转float。4组原生片段确认。候选从实际IFE末segment base+delta重建端点，不能称已恢复Android metadata65th。RGB必须同曲线。CST/CV用既有400诊断转换对，经本轮实际模式验证；IFE CCM保留原阶段、所选IPE CCM所有叶identity。

r2固定5004us／gain1／WB1／同IFE CCM：旁路、色彩回环、Gamma回环各24图，共72IPE direct成功。Y/U/V平均绝对差均<1码值，边缘最大18，非无损。r3原厂模式图、现场普通IPA、现场隔离IPA各24图，共72IPE成功。合计144图、108次数学提交，其中原厂三组63次（22/22/19）；全部观测摘要→准备→同SOF queue→最终成功回执匹配，无未决数值history。普通／隔离现场有12/13组曝光增益WB更新，实拍testPattern0。非零原厂程序相对中性回环312864字节变化，平均差10.8，不能推断画质必然改善。现场样本近距离物体明显失焦或遮挡，未触发AF，不能验收锐度色准噪声。

最终383jobs=completed=direct，failed/cancel/first_error0，starts/stops23；users/running/fatal/pinned/orphans0，owner_refs53桌面CAMSS。两个事务均新增内核故障0／无dump，core电源域／时钟所有权／IRQ／映射／DMA／导入释放，PW/WP各恢复1。taint512历史417保留，不重启清历史。私有输出 /mnt/e/edk2-samurai-out/kernel423，手机 k423-tone-r2/r3 都terminal且无worker/client/collector活跃，样本保留。正式420 r31/r26与419生产驱动／Image363/DT389/CAMSS389/FW/SGowner保持；不能把候选当已安装。

## 已保留失败／直接接续

最初prepare误认为reset只有一处，实际init/configure两处；提前build且build中修改source留下过期对象。build-r2退出0但编译core仍请求IPA2，r1手机枚举失败，IPE作业没增长且恢复无新fault。已强制重编所有调用方／生成接口，产物反汇编确认IPA3后才r2/r3。勿复用失效r2 core；build-r2-validation明确runtime_deployable=false，失败日志保留。测试夹具也曾尺寸和BG网格／长度错误，正确被拒绝，未放宽生产校验；最终SDK用有效16×16夹具，手机实际统计不改。

接续重点：完善当前已接通的单曝光策略，核实完整GTM／HDR／人脸生命周期、原厂65th metadata来源，导出证明LTM DC粗级统计内容/IP依赖，不能用标志1或像素变化代替。当前缺BG／无有效lux的已有观测会拒绝新计算，应补复用已提交曲线的恢复；选择相关用例验证即可。后续再扩展其他摄像头／视频模式，正确构建配套包部署，最后做有清晰场景和AF的画质／连续AE验证。全多摄scope仍reference/kernel363/REMAINING-CAMERA-SCOPE.md，第五2MP身份/mux不要猜OV02A10。底层分层处理，无应用滤镜。

每次WSL source/build/ext4访问先root调用storage284.mounted_build挂原32GiB镜像，不重建／格式化。root Unicorn PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。先等编译进程terminal，再改其输入源码／部署；不要重复423早期竞态。原厂表／ELF／汇编／日志／图像私存，公共仅作者代码及脱敏摘要。本地scoped mirror提交保护无关index，不push。保护NV/OTP/备份/密钥及电池温控。无活动构建或SDK bind。
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从423主摄单曝光TMC/LTM实际闭环继续，读NEXT-SESSION和423README。已接真实触发／BHIST／IFEgreen与lux／同帧6008B request／最终数值history；144真实IPE帧全部成功，108次数值提交，普通及隔离现场实拍已验，色彩Gamma回环误差<1码值。候选IPA3/core配套，正式仍420 r31/r26+419驱动。r1因早期build中改source残留旧IPA2调用对象而枚举失败，已强制重编并检查产物，禁止复用失效r2 core。383direct/0failed/cancel、23starts/stops、服务恢复、资源释放、taint512历史保留。私有系数图像不导出。接下来完善GTM/HDR/人脸及端点来源、LTM DC统计内容/IP依赖、缺BG/lux时持有已确认曲线、其他摄像头和视频模式，再配套打包和清晰场景画质验证。单曝光unity策略不是Android AEC双槽，不声称完整OEM或多摄适配完成。不重跑旧矩阵/事务。WSL先storage284、构建terminal后再改输入，本地提交不push。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 d.update(stage=423,latest_work_stage=423,current_device_revalidated_stage=423,in_progress_installed=False,
  ipe_candidate_private_ipa_version=3,ipe_numeric_tmc_ltm_history_integrated=True,ipe_numeric_tmc_ltm_history_installed=False,
  ipe_media_request_iq_ipa_parameter_generation_integrated=True,ipe_numeric_static_library_built_not_runtime_referenced=False,
  ipe_single_exposure_main_auto_scene_hardware_verified=True,ipe_auto_scene_hardware_evidence=prefix+'reference/kernel423/hardware-validation.json',
  ipe_auto_tone_scope='423 temporary IPA3 candidate: main4608x3456 single-exposure linear-AE/no-face,unity DRC/HDR split;144 real IPE images,108 numeric commits.Native and isolated optical scene captured;full OEM GTM/HDR/DC statistics/quality and other cameras not complete.',
  ipe_full_factory_tone_pipeline_complete=False,ipe_auto_tone_evidence=prefix+'reference/kernel423/README.md')
 p.write_text(json.dumps(d,indent=2)+'\n')
note='423当前：主摄单曝光原厂TMC／LTM已接实际IPA触发、同帧MediaRequest及最终数学历史，144帧实拍成功、108次提交；色彩／Gamma回环误差小于1码值。候选IPA3未永久安装，正式仍r31/r26与419驱动；完整OEM／多摄画质仍未完成。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel423/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel423/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel423/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('422当前：');p.write_text(note+'[423证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';text=p.read_text();needle='[422 原厂数值帧组装与自动链路边界](reference/kernel422/README.md)';assert needle in text;p.write_text(text.replace(needle,'[423 主摄自动TMC／LTM与实拍](reference/kernel423/README.md)'))
print(json.dumps(dict(stage=423,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,main_single_exposure_runtime_hardware_complete=True,full_goal_complete=False,passed=True)))
