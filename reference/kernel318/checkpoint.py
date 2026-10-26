"""Update current progress records and mirror changed sources only."""
from pathlib import Path
import json,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
source=json.loads((HERE/'source-state.json').read_text())
assert json.loads((HERE/'install-r1-validation.json').read_text())['passed']
coverage={};runs={}
for run in ['r4','r5']:
 d=json.loads((host.PRIVATE/('probe-'+run+'-observation.json')).read_text());r=d['state']['summary']
 runs[run]={'overall_passed':r['passed'],'deployment_restored':r['deployment_restored'],'fault_delta':r['fault_delta'],'failure':d['failures']}
 coverage.update({m:c for m,c in r['captures'].items() if c['probe_passed'] and c['cleanup_restored']})
(HERE/'camera-compatibility-validation.json').write_text(json.dumps(dict(stage=318,cameras=coverage,source_runs=runs,passed={'s5kgw1','imx471','imx319','s5k3m5'}<=set(coverage),ambient_scene_not_optical_calibration=True),indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text())
d.update(stage=318,current_camss_module_stage=318,current_camss_module_sha256=source['module_sha256'],current_camss_module_note_sha256=source['module_note_sha256'],
 current_camss_install_evidence='../../reference/kernel318/install-r1-validation.json',current_camss_original_backup='/var/lib/samurai/k318-install-r1/qcom-camss-before.ko',
 current_camss_source_tree=source['tree'],current_camss_source_branch=source['branch'],current_camss_source_commit=source['head'],
 in_progress_stage=318,in_progress_evidence='../../reference/kernel318/README.md',in_progress_installed=True,
 lsc_kernel_parameter_block_implemented=True,lsc_hardware_programmed=True,lsc_hardware_gain_and_geometry_verified=True,
 lsc_enabled_by_default=False,lsc_mode_resampling_implemented=False,lsc_individual_values_applied=False)
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/packages/libcamera/source-lock.json';d=json.loads(p.read_text());d['matched_camss_driver_stage']=318
d['camss_lsc_optional_driver_validation']='reference/kernel318/install-r1-validation.json';p.write_text(json.dumps(d,indent=2)+'\n')
handoff='''# 当前检查点：318

2026-10-20。多摄／骁龙ISP完整目标active、未完成。用户已关灯休息；继续离线／源码／内部图案，正常照明下的光学校准留待方便时。遵循WORKING-BOUNDARIES.md，按改动选择验证，复用未改基线。

318 CAMSS已安装：规则17×13 LSC参数和硬件DMI，默认关闭。统一、横纵渐变、分通道增益、非零起点与细分在S5K3M5内部灰阶图通过；单位／关闭逐字恢复，39,936平坦像素与独立RGB增益模型最大差2.403/255。真实模组校准表未应用。详见reference/kernel318/README.md及linux-port/camera/deployment-lock.json。

当前298 Image＋305 S5K3M5＋318 CAMSS，libcamera 99990.7.2-r25、config/stack 0.1.0-r20、PW/SPA/Gst1.6.9-r3。默认硬件NV12＋AE/AWB、RDI RAW、CPU对比度单次AF保持。四摄分别硬件NV12通过；安装后GStreamer／PipeWire广角各12帧，四摄节点正常。PW实际MemFd，不声称端到端零拷贝。

全部318 worker终态，PW/WP4071/4074，相机及两CCI休眠，故障增量0、taint0。原严格密钥USB SSH169.254.42.1，kernel318/host.py提供raw_ssh；状态切换使用305同启动guard，普通只读无需逐条检查。

内核树/home/cy122/x2pro-linux/camera318-lsc-kernel，samurai-lsc318，提交7f2de88ea5576457cd332b2383ad887e72c6698c，tracked clean。模块SHA2f8a94f5bd34694d52a0ff262f7df668d5cbea46a2109fa5b195d510f50547fa，加载note SHA6ebc03a5c7a1f908252a392fdc8cf2835a78d97adf4972e575ff987ccb0a4863。314备份/var/lib/samurai/k318-install-r1/qcom-camss-before.ko，316旧包／309回退和本地签名仓库保留。318首次安装假设314前置，不重放；临时探测按当前modprobe恢复。

完整r25包源仍在SDK /home/cy122/x2pro-linux/libcamera214-root/work/libcamera316-r25-built/src/libcamera-v0.7.2。原work/libcamera恢复，work/libcamera299-inline仍315，不用旧生成器覆盖316。314／309内核树保留。

继续用户空间模式网格重采样、配置选择／IPA合成。317已取得7个IFE根、7golden、75基础区域，通用合成／编码器见reference/kernel317。个体候选仍4个零节点，Sunny/Qtech地址相同，模组与golden选择、有效性／checksum未解，不能补造／应用。真实前摄IMX471；试验误写imx616的失败已记录，并非驱动变化。

正式阴影／颜色／黑电平、畸变内参、多摄几何同步、真实曝光时间和连续AF未完成。四颗实体同时工作未验证。315六模式双流／AF及316完整包消费者证据沿用未改部分；旧GPU／modem／SSC问题开放，不声称整机健康。
'''
(ROOT/'NEXT-SESSION.md').write_text(handoff)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续多摄／骁龙ISP完整适配，goal active。用户已关灯休息，继续离线／源码／内部图案；先读NEXT-SESSION.md、WORKING-BOUNDARIES.md和reference/kernel318/README.md。318 LSC硬件网格已部署且默认关闭，四摄兼容与安装后GStreamer／PipeWire通过。下一步模式重采样、IPA接入及原厂个体表零节点／模组绑定／校验规则；真实个体表未应用，完整光学与几何校准未完成。不要重放旧前置安装事务。\n')
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json','linux-port/packages/libcamera/source-lock.json']]
for p in paths:
 target=mirror/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
print('Updated318 deployment records and mirrored changed sources.')
