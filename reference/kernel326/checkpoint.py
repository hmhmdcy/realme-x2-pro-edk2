from pathlib import Path
import json,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['descriptor-source-validation.json','read-plan-validation.json','read-r2-validation.json','transfer-validation.json','unit-decode-validation.json','decoder-crosscheck-validation.json','read-ae1-validation.json','ae-reference-validation.json','final-state-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
for run in ['r1','r2','ae1']:
 d=json.loads((host.PRIVATE/('read-'+run+'-observation.json')).read_text());assert d['state']['terminal'] and not d['worker_live']
final=json.loads((HERE/'final-state-validation.json').read_text());pw=final['services']['pipewire'][0]['pid'];wp=final['services']['wireplumber'][0]['pid']
data={m:dict(stage=326,bytes=n,two_reads_equal=True,primary_lsc_nonzero=True,applied=False) for m,n in [('s5kgw1',9984),('imx471',5682),('s5k3m5',12272)]}
data['imx319']=dict(stage=299,decode_stage=320,bytes=12287,two_reads_equal=True,primary_lsc_nonzero=True,applied='temporary322')
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text());d.update(
 current_camera_evidence='../../reference/kernel326/README.md',final_health_evidence='../../reference/kernel326/final-state-validation.json',
 in_progress_stage=326,in_progress_evidence='../../reference/kernel326/README.md',in_progress_installed=False,
 individual_eeprom_data=data,all_four_primary_unit_lsc_decoded=True,individual_decode_evidence='../../reference/kernel326/unit-decode-validation.json',
 individual_decode_independent_evidence='../../reference/kernel326/decoder-crosscheck-validation.json',
 tele_lsc_illuminant2_gr_low_byte_descriptor_anomaly=True,tele_lsc_descriptor_anomaly_repaired=False,
 master_ae_reference_at_legacy_0x3400_valid=False,factory_ae_sync_coefficients_applied=False,ae_reference_evidence='../../reference/kernel326/ae-reference-validation.json',
 system_services=dict(stage=326,services={k:[x['pid'] for x in v] for k,v in final['services'].items()},evidence='../../reference/kernel326/final-state-validation.json'))
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/kernel/source-lock.json';d=json.loads(p.read_text());d.update(in_progress_stage=326,in_progress_evidence='../../../reference/kernel326/README.md',in_progress_installed=False,
 current_camera_evidence='../../../reference/kernel326/README.md',final_health_evidence='../../../reference/kernel326/final-state-validation.json',
 all_four_primary_unit_lsc_decoded=True,individual_eeprom_evidence='../../../reference/kernel326/transfer-validation.json',individual_lsc_decode_evidence='../../../reference/kernel326/unit-decode-validation.json')
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：325','# 当前检查点：326')
begin=s.index('当前所有321～325');end=s.index('\n\n已部署CAMSS318',begin)
s=s[:begin]+f'''当前所有321～326构建/安装/采集worker终态。326三摄完整EEPROM双读和额外AE小读完成，媒体/控制恢复，五sensor/lens、CAMSS/两CCI休眠、九相机电源关闭用户0，相关故障增量0、taint0。PW/WP pid{pw}/{wp}、uid10000。原严格密钥USB SSH169.254.42.1；reference/kernel326/host.py提供raw_ssh。状态切换沿用305 guard /var/lib/samurai/k305-geometry-r2/boot-id-private.txt；普通只读不逐条检查。本轮未更换模块/包/Image/DT、未刷写/重启、未写EEPROM/OTP/NV/persist。'''+s[end:]
begin=s.index('其它摄像头EEPROM前缀已从原BIN核出：');end=s.index('\n\n继续动态AEC/CCT',begin)
s=s[:begin]+'''326已完成其余三摄个体读取：两份GW1描述与当前vendor指纹相同而复用，前摄/长焦版本不同，已ro/noload/noexec取当前文件并卸载。按当前类型表验证主摄0x50/9984 bytes、前摄0x54/5682、长焦0x50/12272，地址16bit、READ枚举3。使用系统cam --capture=0并等待首个成功帧持有供电，I2C只发2字节地址指针再READ；各完整双读相同、传回核对。R1因缺/proc/PID/task/PID/children而在实际EEPROM前失败并恢复，改stat PPid+pidfd后R2全部通过，380帧仅供电期间观察，无图像文件。三摄全部主LSC884值非零，WB分母正；主/长焦LSC起点208，前摄512，沿用本机HAL每51点跳1字节，主摄旧步长会有3假零。独立C顺序游标/Python随机地址、host和ARM各7072值完全一致。reference/kernel326/README.md。

正确新个体数据/private kernel326/reads-r2/{s5kgw1,imx471,s5k3m5}-read{1,2}-private.bin；decoded-unit-private.json含当前描述逐光源WB/LSC、未应用。descriptor-layouts-private.json含当前类型行；descriptor-sources-private.json定位主摄115缓存及326新前摄/长焦文件。光源0主表可用于明确诊断配置。注意长焦光源2的GR低字节在原厂写208而正常packed40为209，必须保留事实并明确选择光源，不把5项都当alias同表；本轮没有修补任何值。其它三摄仍未做个体实际应用，默认仍不启用。下一步用326主表/golden及已有模式映射做可回退配置试验，不要把未知checksum变成所有实验硬门槛。

AE同步进一步事实：已查本机HAL旧命名GW1分支0x50323c/0x503250，主参考偏移0x3400、36bytes；位于当前9984常规段之外，另正常供电小读双读一致。该位置命中拒绝哨兵0xff，没有可用主参考，不能据此应用同步系数。新文件/private kernel326/reads-ae1/s5kgw1-ae-master-read{1,2}-private.bin。广角299及长焦326的0x2d00数字字段非零，长焦共同布局仍候选；decoded-ae-reference-private.json保留结果。旧分支接受s5kgw1_p24c128e_sunny/_19696，而当前Sunny描述为_19781；不能强认版本完全一致。继续主参考正确来源/旧persist只读备份调查时先找现存资料，不盲扫或重读旧0x3400。未写persist。

326 /var/lib/samurai/k326-eeprom-r1失败恢复、r2完整读取完成、ae1小读完成，均终态。当前打包read.tar.gz最后为ae-read-plan.json，不盲目复用launch-read重读。下轮继续实测新个体配置及动态调校。'''+s[end:]
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续多摄/骁龙ISP完整goal。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel326/README.md。部署仍325 GW1+318 CAMSS+305长焦+298 Image，r26/config-r21；四摄factory LSC已出图。326主/前/长焦EEPROM双读、主表解码及host/ARM独立对照通过，正确值kernel326/decoded-unit-private.json，尚未应用，下一步合成/实测可回退unit配置和动态触发。长焦光源2 GR地址208异常保留，选光源0诊断。主AE旧0x3400位置小读为空拒绝，别重复或假称主参考恢复；参考源版本名不完全匹配。未知checksum不是全部实验硬门槛；用户关灯继续独立工作。全部worker终态，勿盲目重放旧事务。\n')
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded326 acquired/decoded unit data and negative legacy AE offset; sources/evidence mirrored, goal active.')
