"""Record the new temporary unit application; deployed packages stay unchanged."""
from pathlib import Path
import json, shutil
import host

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for name in ['profile-assembly-validation.json', 'probe-r1-validation.json',
             'ipa-mesh-validation.json', 'unit-image-validation.json', 'final-state-validation.json']:
    assert json.loads((HERE / name).read_text())['passed']
observation = json.loads((host.PRIVATE / 'probe-r1-observation.json').read_text())
assert observation['state']['terminal'] and not observation['worker_live']
final = json.loads((HERE / 'final-state-validation.json').read_text())
pw = final['services']['pipewire'][0]['pid']
wp = final['services']['wireplumber'][0]['pid']
for relative, prefix in [('linux-port/camera/deployment-lock.json', '../../'),
                         ('linux-port/camera/kernel/source-lock.json', '../../../')]:
    p = ROOT / relative
    d = json.loads(p.read_text())
    d.update(current_camera_evidence=prefix + 'reference/kernel327/README.md',
        final_health_evidence=prefix + 'reference/kernel327/final-state-validation.json',
        in_progress_stage=327, in_progress_evidence=prefix + 'reference/kernel327/README.md',
        in_progress_installed=False, individual_eeprom_values_applied=True,
        individual_eeprom_values_applied_scope='temporary LSC profiles only: wide322, main/front/tele327; full calibration and installed defaults incomplete',
        all_four_camera_unit_lsc_runtime_verified=True,
        individual_lsc_runtime_evidence=prefix + 'reference/kernel327/unit-image-validation.json',
        individual_lsc_serialization_evidence=prefix + 'reference/kernel327/ipa-mesh-validation.json')
    if 'deployment-lock' in relative:
        d.update(lsc_individual_values_applied_scope='temporary internal-pattern profiles: wide322, GW1 both unbound factory branches/front/tele327; defaults unchanged',
            lsc_individual_hardware_evidence=prefix + 'reference/kernel327/unit-image-validation.json',
            lsc_main_individual_values_applied=True, lsc_front_individual_values_applied=True,
            lsc_tele_individual_values_applied=True,
            lsc_individual_default_enabled=False, lsc_dynamic_scene_trigger_integration=False,
            full_automatic_hardware_pipeline_ipa_incomplete_scope='Formal optical image quality, EEPROM checksum/binding and automatic application, dynamic LSC triggers, multi-camera geometry/synchronization, exposure timestamps, continuous AF and deliberate event-loss recovery remain incomplete.',
            system_services=dict(stage=327, services={k: [x['pid'] for x in v] for k, v in final['services'].items()},
                evidence=prefix + 'reference/kernel327/final-state-validation.json'))
        for model in ['s5kgw1', 'imx471', 's5k3m5']:
            d['individual_eeprom_data'][model]['applied'] = 'temporary327-explicit-illuminant0'
    else:
        d['spectra_hardware_image_processing_supported_scope'] = 'Installed r26 camss-vfe hardware NV12/AE/AWB plus RAW; factory LSC tests through325 and four-camera temporary unit LSC through327, optical calibration incomplete'
    p.write_text(json.dumps(d, indent=2) + '\n')
p = ROOT / 'NEXT-SESSION.md'
s = p.read_text().replace('# 当前检查点：326', '# 当前检查点：327')
begin = s.index('当前所有321～326')
end = s.index('\n\n已部署CAMSS318', begin)
s = s[:begin] + f'''当前所有321～327构建/安装/采集worker终态。327三摄主表/golden成对LSC采集14例和独立编码/图像分析通过；媒体/控制恢复，CAMSS/两CCI休眠、九相机电源关闭用户0，相关故障增量0、taint0。PW/WP pid{pw}/{wp}、uid10000。原严格密钥USB SSH169.254.42.1；reference/kernel327/host.py提供raw_ssh。状态切换沿用305 guard /var/lib/samurai/k305-geometry-r2/boot-id-private.txt；普通只读不逐条检查。本轮未更换模块/包/Image/DT、未刷写/重启、未写EEPROM/OTP/NV/persist。''' + s[end:]
s = s.replace('尚无长焦个体应用。reference/kernel323/README.md。', '当时尚无长焦个体应用，327已补齐临时光源0实测。reference/kernel323/README.md。')
s = s.replace('其它三摄仍未做个体实际应用，默认仍不启用。下一步用326主表/golden及已有模式映射做可回退配置试验，不要把未知checksum变成所有实验硬门槛。',
    '326当时未应用三摄值；327已补齐光源0可回退配置试验，默认仍不启用。不要把未知checksum变成所有实验硬门槛。')
s = s.replace('下轮继续实测新个体配置及动态调校。', '后续327已实测新个体配置，继续动态调校。')
insert = '''327：复用325通用lsc-smoke与313fixture，三摄新增14个factory/unit配对配置，主摄Qtech/Sunny两分支各两模式、前摄两模式、长焦一模式，均通过当前r26 IPA到硬件。仅显式Default UID25/lux100/CCT6500/LED0/EEPROM光源0诊断，主摄供应商仍未绑定；不选择/修补长焦光源2。真实AArch64 IPA 14份1792-byte块与独立Hermite/float32模型共12376个Q10值完全一致。7组unit图像均不同factory，7份factory与已有参考逐字节相同；旧off基线复用，unit近似图像模型p99主摄1.68～1.80、前摄1.49～1.54、长焦1.17/255。不是RAW/正常照明校准。四摄真实unit临时应用链路至此齐全（广角322）；默认未启用，动态CCT/AEC尚未集成。reference/kernel327/README.md。

327私有配置kernel327/profiles/{qtech_s5kgw1,sunny_s5kgw1,sunny_imx471,qtech_s5k3m5sx}-{factory,unit}.yaml；14案例reference/kernel327/cases.json；图像kernel327/images-r1、真实IPA网格*-mesh-private.bin。AArch64多模式导出工具SDK/private/camss327-mesh/dump及public dump-ipa-mesh.cpp，仅主机chroot运行，不在手机安装。手机/var/lib/samurai/k327-lsc-r1终态、恢复成功；无需重复旧工厂采集/完整包回归，后续从动态触发、供应商绑定/WB以及AE参考正确来源推进。

'''
place = s.index('继续动态AEC/CCT触发')
s = s[:place] + insert + s[place:]
p.write_text(s)
(ROOT / 'NEXT-SESSION-PROMPT.md').write_text('继续多摄/骁龙ISP完整goal。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel327/README.md。部署仍325 GW1+318 CAMSS+305长焦+298 Image，r26/config-r21。327三摄unit主表/golden临时配置14例采集/12376值真实IPA编码/7组成对图像通过，四摄unit链路齐全（广角322），默认未启用、供应商/光源/动态AEC-CCT未完成；下一步继续动态调校/WB/正确AE来源。长焦光源2地址异常保留，本轮仅光源0。主AE旧0x3400为空拒绝，别重复或声称恢复。用户关灯可继续源码与内部图案；全部worker终态，勿重放旧事务或添加繁琐全量验证。\n')
p = ROOT / 'linux-port/camera/README.md'
s = p.read_text()
banner = '327当前：r26/config-r21与325 GW1/318 CAMSS部署保持；主/前/长焦个体LSC主表已通过临时配置实际应用，加上322广角，四摄链路齐全。14份IPA网格与独立模型完全一致，7组成对图像显示补偿效果；默认及动态调校、正常光照/几何同步校准仍未完成。[327实测](../../reference/kernel327/README.md)。以下为历史记录。\n\n'
if not s.startswith('327当前：'): p.write_text(banner + s)
mirror = Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT / n for n in ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md',
    'linux-port/camera/README.md', 'linux-port/camera/deployment-lock.json', 'linux-port/camera/kernel/source-lock.json']]
for source in paths:
    target = mirror / source.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
print('Recorded327 temporary four-camera unit LSC evidence and mirrored public sources; goal remains active.')
