from pathlib import Path
import hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
install=json.loads((HERE/'install-r1-validation.json').read_text());assert install['passed'] and install['transaction']['installed']
artifacts=json.loads((HERE/'package-artifact-validation.json').read_text())
product=json.loads((host.PRIVATE/'product-r1-observation.json').read_text());assert product['state']['terminal'] and not product['worker_live'] and product['state']['summary']['passed']
(HERE/'product-r1-validation.json').write_text(json.dumps(product['state']['summary'],indent=2)+'\n')
for package,changed in [('libcamera',['APKBUILD','0030-camss-lens-shading.patch']),('samurai-camera-config',['APKBUILD'])]:
 dest=ROOT/'linux-port/packages'/package
 for name in changed:shutil.copyfile(HERE/'recipes'/package/name,dest/name)
 p=dest/'source-lock.json';d=json.loads(p.read_text());d.update(stage=321,build_stage=321,
  package_version='99990.7.2-r26' if package=='libcamera' else '0.1.0-r21',
  actual_signed_build_validation='reference/kernel321/package-build-validation.json',
  native_install_validation='reference/kernel321/install-r1-validation.json',actual_current_payload_validation='reference/kernel321/install-r1-validation.json',
  matched_camss_driver_stage=318,lsc_ipa_implemented=True,lsc_static_mode_upload=True,lsc_default_enabled=False)
 for name in changed:d['source_files_sha256'][name]=hashlib.sha256((dest/name).read_bytes()).hexdigest()
 p.write_text(json.dumps(d,indent=2)+'\n')
 readme=dest/'README.md';old=readme.read_text()
 readme.write_text('321当前：r26/config-r21已部署，318 CAMSS保持。LSC的IPA合成、模式重采样及启动参数上传完成，真实内部图案链路通过；默认个体LSC尚未启用。四摄取流及安装后GStreamer／PipeWire通过，正式光学与多摄校准仍在继续。[321证据](../../../reference/kernel321/README.md)。以下为历史。\n\n'+old)
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text())
d.update(stage=321,framework_version='99990.7.2-r26',configuration_version='0.1.0-r21',installed_camera_packages=install['transaction']['packages'],built_packages=artifacts['packages'],
 current_camera_evidence='../../reference/kernel321/README.md',final_health_evidence='../../reference/kernel321/install-r1-validation.json',
 current_product_consumer_evidence='../../reference/kernel321/product-r1-validation.json',current_product_install_evidence='../../reference/kernel321/install-r1-validation.json',
 in_progress_stage=321,in_progress_evidence='../../reference/kernel321/README.md',in_progress_installed=True,
 lsc_ipa_integration_implemented=True,lsc_ipa_deployed=True,lsc_static_mode_upload=True,
 lsc_native_ipa_hardware_evidence='../../reference/kernel321/native-r2-image-validation.json',
 lsc_imx319_reference_mapping_evidence='../../reference/kernel321/imx319-mode-mapping-validation.json',
 lsc_enabled_by_default=False,lsc_individual_values_applied=False)
p.write_text(json.dumps(d,indent=2)+'\n')
state=json.loads((HERE/'source-state.json').read_text());state.update(installed=True,incremental_patch='0030-camss-lens-shading.patch',patch_applies_to316=True,package_recipe='recipes/libcamera/APKBUILD')
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
handoff='''# 当前检查点：321

2026-10-20，多摄／骁龙ISP完整目标active。用户已关灯睡觉，继续源码／原厂数据／内部图案工作，不把暗室普通图像当作正常照明校准。遵循WORKING-BOUNDARIES.md：按改动选择必要验证，复用未改基线，不重设繁琐门槛。

现已部署libcamera 99990.7.2-r26、config/stack 0.1.0-r21，内核仍298 Image＋305 S5K3M5＋318 CAMSS。321将golden/unit合成、GR/GB均衡、模式网格重采样和LSC启动参数接入IPA；静态表只上传revision0，后续AWB更新仍56字节。默认四摄YAML不启用真实个体LSC。实现和证据见reference/kernel321/README.md及linux-port/camera/deployment-lock.json。

实际AArch64 DSO契约通过；IMX319内部灰阶图完整IPA→参数→硬件→NV12链路通过关闭／单位／统一增益／二维渐变／合成增益。单位逐字等于关闭；43,008内部像素模型99百分位误差≤1.929/255，最大8.875/255。不是独立RAW或正式光学测量。包共13个、6个IPA，四摄分别GStreamer640x480通过，安装后GStreamer／PipeWire广角各12帧，四节点正常。315/316未改RAW／双流／AF／高分辨率证据沿用。

全部321构建／采集／安装worker终态，当前PW/WP pid6642/6645，相机和两CCI休眠，相关故障增量0、taint0。原严格密钥USB SSH169.254.42.1，kernel321/host.py提供raw_ssh；状态切换沿用305同启动guard，普通只读无需逐条检查。模块note SHA6ebc03a5c7a1f908252a392fdc8cf2835a78d97adf4972e575ff987ccb0a4863，仍318；未刷写／重启／写EEPROM、OTP、NV或persist。

321回退材料/var/lib/samurai/k321-install-r1，旧r25/r20包与world／仓库配置已保留。其首次安装假设r25/r20前置，不在r26/r21上重放。318模块备份/var/lib/samurai/k318-install-r1/qcom-camss-before.ko；更早316回退保留。

最新完整包源/home/cy122/x2pro-linux/libcamera214-root/work/libcamera321-lsc-built/src/libcamera-v0.7.2。316源保留，原work/libcamera恢复；work/libcamera299-inline仍315。不要用旧生成器覆盖321。正式配方含原29补丁＋0030，增量patch已在r25源dry-run通过。内核树camera318-lsc-kernel仍7f2de88ea5576457cd332b2383ad887e72c6698c。

320已解释原4个零节点：本机HAL每51个packed40点额外跳过1字节（四处0xff），地址208+5*i+floor(i/51)。修正后884值全非零，C/Python、主机/ARM、两读一致；无数据修补或写回。私有正确值及候选因子在kernel320/stock-unit-lsc-private.json，原始两读仍kernel299。参考kernel320/README.md；不能再把4零当当前阻塞。

IMX319当前stock mode2的模拟3280x2448、bin2x2、数字裁剪左4，对应mode0输出3264x2448，两者物理原点(8,8)。固定CamX用mode0输出作LSC域，该约定映射source_span1631/1223、first_quad0/0、step2/2。当前驱动几何寄存器与原厂相同；本机HAL的fullResolution赋值未独立反汇编，勿把整个公开CamX版本当完全相同。新的YAML接口显式描述坐标，不以模拟窗口/输出尺寸猜binning。

下一步：将7个原厂LSC根（2种golden、17种基础表）与Default/Sensor/Usecase/Feature选择关联，结合320正确单位数据做可回退的真实校准配置试验；继续核查原厂有效性约定。尚未发现checksum不应阻止所有只读分析／可回退实验，也不能假称校验完成。真实个体LSC尚未应用。继续其它三摄对应调校、正常光线的阴影／颜色／黑电平、畸变内参、多摄几何同步、真实曝光时间和连续AF。四实体同时工作未验证；旧GPU/modem/SSC问题开放。目标不可缩减为已完成的兼容功能。
'''
(ROOT/'NEXT-SESSION.md').write_text(handoff)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续多摄／骁龙ISP完整适配，goal active。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md及reference/kernel321/README.md。已部署r26/config-r21＋318 CAMSS；LSC的IPA合成与重采样、实际内部图案链路、四摄消费者及安装后GStreamer/PipeWire通过。真实个体LSC默认未启用。320分组解码已消除原4零，勿当阻塞；继续原厂模式／触发选择和真实校准配置试验及多摄校准。用户已关灯，继续独立工作；未知checksum不是所有可回退实验的硬门槛。\n')
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json']]
for package,names in [('libcamera',['APKBUILD','0030-camss-lens-shading.patch','source-lock.json','README.md']),('samurai-camera-config',['APKBUILD','source-lock.json','README.md'])]:paths += [ROOT/'linux-port/packages'/package/name for name in names]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Promoted r26/r21 recipes, deployment evidence and concise321 handoff.')
