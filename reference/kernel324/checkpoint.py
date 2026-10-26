from pathlib import Path
import json,shlex,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['factory-source-validation.json','factory-lsc-validation.json','mode-profile-validation.json','native-r3-validation.json','native-r3-image-validation.json','module-calibration-prefix-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
for run in ['r1','r2','r3']:
 d=json.loads((host.PRIVATE/('probe-'+run+'-observation.json')).read_text());assert d['state']['terminal'] and not d['worker_live'] and d['state']['summary']['deployment_restored']
code='''
from pathlib import Path
import json
services={}
for name in ['pipewire','wireplumber']:
 rows=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name:rows.append(dict(pid=int(p.name),uid=p.stat().st_uid))
  except (FileNotFoundError,ProcessLookupError):pass
 services[name]=rows
assert all(len(v)==1 and v[0]['uid']==10000 for v in services.values())
print(json.dumps(dict(stage=324,services=services)))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);services=json.loads(q.stdout)
(HERE/'restored-services-validation.json').write_text(json.dumps(services,indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text());d.update(
 current_camera_evidence='../../reference/kernel324/README.md',final_health_evidence='../../reference/kernel324/native-r3-validation.json',
 in_progress_stage=324,in_progress_evidence='../../reference/kernel324/README.md',in_progress_installed=False,
 lsc_main_factory_trigger_tree_decoded=True,lsc_main_supplier_binding_verified=False,lsc_main_hardware_profile_verified=False,
 lsc_front_factory_trigger_tree_decoded=True,lsc_front_factory_profile_temporarily_applied=True,lsc_front_individual_values_applied=False,
 lsc_front_verified_sensor_modes=[[2304,1728],[1928,1088]],lsc_front_hardware_evidence='../../reference/kernel324/native-r3-image-validation.json',
 gw1_standard_test_pattern_control_implemented=False,gw1_color_bars_manufacturer_source='../../reference/kernel324/gw1-pattern-primary-source.json',
 system_services=dict(stage=324,services={k:[x['pid'] for x in v] for k,v in services['services'].items()},evidence='../../reference/kernel324/restored-services-validation.json'))
p.write_text(json.dumps(d,indent=2)+'\n')
pw=services['services']['pipewire'][0]['pid'];wp=services['services']['wireplumber'][0]['pid']
handoff=f'''# 当前检查点：324

2026-10-20，多摄/骁龙ISP完整goal active，不能只以现有兼容功能算完成。用户已关灯睡觉；继续离线、源码、内部图案工作，不把暗室普通帧当正常照明校准。遵循WORKING-BOUNDARIES.md，复用未改基线，不加全量重复验证/任意帧数门槛。

现机：libcamera 99990.7.2-r26、config/stack 0.1.0-r21（321安装），PW/SPA/Gst1.6.9-r3；298 Image＋305 S5K3M5＋318 CAMSS。default camss-vfe硬件NV12/AE/AWB；RAW和RAW+NV12、主摄单次AF/取消有315/316证据。MemFd而非端到端zero-copy。默认四摄YAML不启用个体LSC；r26已实现可选静态LSC、golden/unit合成和模式重采样，revision0上传、后续AWB仍56字节。

当前所有321～324构建/安装/采集worker终态。324 R1/R2失败但恢复，R3前摄两模式off/factory成功；/var/lib/samurai/k324-lsc-r3终态。PW/WP pid{pw}/{wp}、uid10000，相机/两CCI休眠，九相机电源关闭用户0，相关故障增量0、taint0。原严格密钥USB SSH169.254.42.1；reference/kernel324/host.py提供raw_ssh。状态切换沿用305 guard /var/lib/samurai/k305-geometry-r2/boot-id-private.txt；普通只读不逐条检查。无本轮模块/包替换、刷写、重启或EEPROM/OTP/NV/persist写入。

已部署CAMSS318 SHA2f8a94f5bd34694d52a0ff262f7df668d5cbea46a2109fa5b195d510f50547fa，loaded note SHA6ebc03a5c7a1f908252a392fdc8cf2835a78d97adf4972e575ff987ccb0a4863。内核源/home/cy122/x2pro-linux/camera318-lsc-kernel，分支samurai-lsc318，提交7f2de88ea5576457cd332b2383ad887e72c6698c，未改。LSC17x13四通道Q10、unity1024～8191、内部bank上传与参数队列已实测。内核不存模组表。

最新完整r26包源/home/cy122/x2pro-linux/libcamera214-root/work/libcamera321-lsc-built/src/libcamera-v0.7.2；原work/libcamera已恢复，316源保留。不要用旧315/316生成器覆盖321。linux-port/packages配方含0030。回退r25/r20包/world/repositories在/var/lib/samurai/k321-install-r1，318旧模块在k318-install-r1/qcom-camss-before.ko。不要在r26上重放首次安装。

320已纠正IMX319个体packed40：每51点额外跳1字节，地址208+5*i+floor(i/51)，884值全非零，不修补原数据。正确值/private kernel320/stock-unit-lsc-private.json，原始双读kernel299。不要使用304/317旧单位解码/旧候选零点结论。Checksum仍未确认，但不能把它变成所有可回退运行配置试验的硬门槛，也不能假称校验完成。

322：广角七原厂LSC根完整触发树/表/golden与XML对应，三套配置。Default25/130、Usecase33为1262、PreviewFeature1.12四根相同。区间内保持、仅间隙线性插值。显式Default/lux100/CCT6500的factory与真实unit均通过已安装IPA→318硬件内部灰阶图；两份884编码字与独立模型完全一致。真实个体LSC已临时应用，默认未启用。mode2对应mode0域span1631/1223、first0/0、step2/2。reference/kernel322/README.md。

323：长焦六根94基础/6golden完整对应，三套。Default25/278/488；625另有LED1，组装器已支持显式LED索引，不默认选择多分支。本轮LED0，396组触发通过。mode3 2104x1560对应mode0 4208x3120，参考起点同8/8；span2103/1559、first0/0、step2/2。factory内部图案已通过系统IPA，尚无长焦个体应用。reference/kernel323/README.md。

324：本机原厂vendor只读取得qtech_s5kgw1、sunny_s5kgw1、sunny_imx471调校，均与298库存指纹匹配，已卸载。三文件各2个IFE LSC根，基础区域5/18/22，golden各2，完整触发树/网格与原厂解析器对应。原始调校/private kernel324/*-tuning-private.bin、解码*-trees-private.json，私有profiles已生成。主摄两文件明显不同且未绑定本机；qtech描述EEPROMName还写Sunny_19696，名字不证明供应商。

324四映射：GW1 4608x3456 span4639/3471 first16/8 step2/2；4608x2592 first16/440。IMX471 2304x1728 span2303/1727 first0/0；1928x1088 first200/302。均按原厂/当前真实裁剪与数字偏移，固定CamX约定用mode0输出域。目标HAL fullResolution赋值仍未独立反汇编；不要说公开版本全部匹配。前摄full4608x3456仍需remosaic，未启用。

324 R1主摄TEST_PATTERN查询返回6，0帧，当前GW1驱动没有该控制。R2前摄off通过，factory因共享gain对象产生YAML alias被拒绝；生成器改为每模式独立副本，复用未改采集二进制重新打包。R3两前摄模式off/factory均实际稳定3帧，ACTIVE尺寸读回确认；近似独立模型p99 1.478/1.541，max4.127/8.851/255，不是RAW光学精度。工具SDK/private/camss324-runtime/lsc-smoke，通过公共SensorConfiguration显式选sensor output；cases.json有10计划案例，但仅前摄4项R3通过，主摄6项不可算通过。reference/kernel324/README.md。

下一步可立即做GW1标准TEST_PATTERN控制：已找到真我官方realme6同GW1源，固定commit0933e0e5b2fd30faa7857f5024a86f3759713374，路径drivers/misc/mediatek/imgsensor/src/common/v1_1/s5kgw1_mipi_raw/s5kgw1mipiraw_Sensor.c，set_test_pattern_mode明确16-bit0x0600=2为Color Bars，0关闭。本机模组BIN只有Off=0。来源/private kernel324/sources/s5kgw1mipiraw_Sensor.c，浅克隆sources/realme6-kernel；公开pin gw1-pattern-primary-source.json。未启用本机，不把别板来源当实际验证。补标准驱动控制后完成主摄LSC；无需发明板级属性/应用私有I2C写寄存器。

其它摄像头EEPROM前缀已从原BIN核出：主摄0x50/9984 bytes、前摄0x54/5682、长焦0x50/12272，均地址16bit、READ枚举3；只是前缀，不是完整校验。模块描述均203Q根、WB15Q×5、LSC17Q×5的位置同304。下一步复用正常V4L2供电持有和标准CCI I2C只读，继续个体布局与绑定。尚未读取这些个体表。324 module-calibration-prefix-validation.json。

继续动态AEC/CCT触发（不能把ExposureValue直接当OEM lux index）、正常光线阴影/颜色/黑电平、畸变内参、多摄几何同步、真实曝光时间和连续AF。四实体同时流未验证；旧GPU/modem/SSC问题开放。完整目标未完成，保持active。
'''
(ROOT/'NEXT-SESSION.md').write_text(handoff)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续多摄/骁龙ISP完整goal。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel324/README.md。r26/config-r21+318保持。322广角真实unit、323长焦factory、324前摄factory两模式已内部图案实际通过；默认未启用。主摄因缺标准TEST_PATTERN尚未验证LSC，已固定真我同GW1源码0x0600=2/0，可立即补标准驱动控制并继续主摄。其余个体EEPROM前缀已核出，可继续读/解码/绑定；未知checksum不是所有可回退实验的硬门槛。用户关灯继续独立工作，正常光学和多摄校准仍待完成。全部本轮worker终态，勿重放旧事务。\n')
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print(json.dumps(services,indent=2));print('Recorded324 with failed attempts preserved; main pattern control remains next, goal active.')
