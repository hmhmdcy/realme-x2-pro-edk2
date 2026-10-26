"""Prepare the minimal gain helper atop the complete maintained r13 stack."""
from pathlib import Path
import difflib,hashlib,json,shutil
R=Path(__file__).resolve().parent;ROOT=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel238');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert not P.exists();P.mkdir(mode=0o700)
(P/'usb-ipv6-candidates-private.json').write_bytes((P.parent/'kernel237/usb-ipv6-candidates-private.json').read_bytes())
(R/'host.py').write_text((R.parent/'kernel237/host.py').read_text().replace('kernel237','kernel238').replace('usb237','usb238').replace('Authenticated237','Authenticated238'))
old=(ROOT/'NEXT-SESSION.md').read_bytes();archive=ROOT/'archive/NEXT-SESSION-through237-2026-10-16.md';assert not archive.exists();archive.write_bytes(old)
(P/'current-work-private.json').write_text(json.dumps(dict(stage=238,state='minimal helper prepared, build and fresh phone baseline pending',guard='/var/lib/samurai/k236-runtime/boot-id-private.txt',active_native_context=None,active_build_session=None,previous_goal_turn_classification='progress',full_peripheral_goal_active=True,next='Build fullr14/r9 preserving original214; inspect actual vendor readonly, then validate helper and explicit RAW metadata/response'),indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-16，238进行中。237为progress，IMX319六帧RAW与前摄RAW/RGB回归通过，后摄近黑待验。完整goal active。[237归档](archive/NEXT-SESSION-through237-2026-10-16.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前状态

仍236启动，guard /var/lib/samurai/k236-runtime/boot-id-private.txt，旧233及更早全部失效。运输reference/kernel238/host.py、私人238/current-work-private.json记录活任务。boot235/MFD6021/lab5198/provider2223/imx319176f/前摄e49/CAMSSff9/FastRPC2abd保持，当前789清单k237-camss-install/module-inventory-after-private.json。手机libcamera r13/config r8尚未改变，GNSS仍无正CNR/fix，无SIM；BT开启1连接只观察，不pair/connect/disconnect。全面状态/回退见237归档。

## 源码、产物与回退依据

238只准备IMX319 gain helper新增0021，保留r13原20补丁/全部管线与子包、5IPA签名输入。SDK /home/cy122/x2pro-linux/libcamera214-root，完整r13缓存/work/libcamera225-r13-built受保护；r14构建时原214 /work/libcamera移入/private/libcamera214-before238-r14，候选保留/work/libcamera238-r14-built。活构建不能移动/重启；终态必须恢复原214全部2254文件/链接/模式。canonical内核仍after228，不刷其旧相机输出。

## 续作与已知风险

先读私人237/next-agent-results-private.md。helper用1024/(1024-code)，2/4/8x为512/768/896，不复制IMX471黑电平/尺寸/延迟。RAW-only须确认CPU统计启用日志，显式start及reuse控制，采集时ExposureTime/AnalogueGain/两Mode元数据，不能用SensorTimestamp证明闭环。曝光2ms/1x→32ms/1x→32ms/8x→返回2ms/1x，固定digital_gain/VBLANK，settle后RAM统计，无照片/灯光/纯色要求。

GNSS先以实际vendor分区版本定版；旧system是Android16自定义ROM，不能猜vendor是Android10。旧115同分区只读提取和231校验可作对应。只读ro,noload/noexec，不读NV/persist、不执行vendor代码；外部C33/C34/F10未经匹配不当本机。S5K3M5下步双投影XML加独立decoder验917init混合WRITE8/16与4x53模式，资源/PLL候选见237私有笔记，不猜VIN或盲开P L2/L6。
''')
cache=SDK/'work/libcamera225-r13-built';source=cache/'src/libcamera-v0.7.2';name='src/ipa/libipa/camera_sensor_helper.cpp';before=(source/name).read_text();assert 'REGISTER_CAMERA_SENSOR_HELPER("imx319"' not in before
addition='''class CameraSensorHelperImx319 : public CameraSensorHelper
{
public:
	CameraSensorHelperImx319()
	{
		/* Linux imx319: gain = 1024 / (1024 - code), code 0..960. */
		gain_ = AnalogueGainLinear{ 0, 1024, -1, 1024 };
	}
};
REGISTER_CAMERA_SENSOR_HELPER("imx319", CameraSensorHelperImx319)

'''
anchor='class CameraSensorHelperImx471';assert before.count(anchor)==1;after=before.replace(anchor,addition+anchor)
patch='Subject: [PATCH] ipa: libipa: add Sony IMX319 analogue gain helper\n\nUse the Linux driver gain-code model without importing calibration or\nstatic optical properties from another sensor.\n\n---\ndiff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(R/'0021-imx319-gain-helper.patch').write_text(patch)
recipe=SDK/'work/libcamera238-r14';config=SDK/'work/samurai-camera-config238-r14';assert not recipe.exists() and not config.exists()
recipe.mkdir();config.mkdir()
for p in (ROOT/'linux-port/packages/libcamera').iterdir():
 if p.is_file() and p.name not in ['README.md','source-lock.json']:shutil.copyfile(p,recipe/p.name)
for p in (ROOT/'linux-port/packages/samurai-camera-config').iterdir():
 if p.is_file() and p.name!='README.md':shutil.copyfile(p,config/p.name)
shutil.copyfile(R/'0021-imx319-gain-helper.patch',recipe/'0021-imx319-gain-helper.patch')
apk=(recipe/'APKBUILD').read_text();assert apk.count('pkgrel=13\n')==1;apk=apk.replace('pkgrel=13\n','pkgrel=14\n').replace('\t0020-soft-invalid-statistics-hold.patch\n','\t0020-soft-invalid-statistics-hold.patch\n\t0021-imx319-gain-helper.patch\n')
at=apk.rfind('\n"');apk=apk[:at]+'\n'+hashlib.sha512(patch.encode()).hexdigest()+'  0021-imx319-gain-helper.patch'+apk[at:];(recipe/'APKBUILD').write_text(apk)
cfg=(config/'APKBUILD').read_text();assert 'pkgrel=8\n' in cfg;cfg=cfg.replace('pkgrel=8\n','pkgrel=9\n').replace('99990.7.2-r13','99990.7.2-r14');(config/'APKBUILD').write_text(cfg)
for dirname,rel in [('libcamera',recipe),('samurai-camera-config',config)]:
 dest=R/'recipes'/dirname;dest.mkdir(parents=True)
 for p in rel.iterdir():
  if p.is_file():shutil.copyfile(p,dest/p.name)
report=dict(stage=238,patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),source_before_sha256=hashlib.sha256(before.encode()).hexdigest(),source_files={name:hashlib.sha256(after.encode()).hexdigest()},new_patch_count=21,prior20_inputs_preserved=True,no_black_level_static_properties_or_delays_copied=True,minimum_gain_helper_only=True,phone_not_modified=True)
(R/'helper-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
