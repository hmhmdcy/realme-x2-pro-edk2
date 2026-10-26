from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['inverse-gamma-validation.json','icp-firmware-collection.json','firmware-queue-validation.json','icp-reuse-assessment.json']:
 assert json.loads((HERE/name).read_text())['passed'],name
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text());d.update(current_camera_evidence=prefix+'reference/kernel352/README.md',in_progress_stage=352,
  in_progress_evidence=prefix+'reference/kernel352/README.md',in_progress_installed=False,
  factory_ltm_inverse_gamma_ported=True,factory_ltm_inverse_gamma_evidence=prefix+'reference/kernel352/inverse-gamma-validation.json',
  factory_icp_firmware_retained=True,factory_icp_firmware_evidence=prefix+'reference/kernel352/icp-firmware-collection.json',
  factory_icp_queue_abi_verified_in_firmware=True,factory_icp_queue_evidence=prefix+'reference/kernel352/firmware-queue-validation.json',
  icp_hardware_backend_installed=False,icp_reuse_evidence=prefix+'reference/kernel352/icp-reuse-assessment.json',
  factory_final_tone_default_pending=True,current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
entry='''352最新：移植libipa/ltm_inverse_gamma.{h,cpp}，64IFE greenbase10→LTM64段base14/delta14，独立结果类型。预重建4096forward、65inverse earliesttie，portable无负数右移。host/ARM各31cases8060bytes与私有编译原source InverseGamma/PackHLUT/utility0diff，缓存命中未命中核对；尚非原HAL指令oracle。首版非单调/突变625bytes差因负delta显式signbit（<-8192不等于简单wrap），已修forward/inverse pack，R1failed报告与旧输出保留。SDK/private/camss352-math小工具，无bind/phoneworker。

352优先搜索找到BOD ICP/BPS/IPE原型ebd1e440...（qcom-laptops-v6.18-rc4-camss-icp-bps-ipe-icp-boots+stats-b4，GoogleGitiles）。只取9file67434bytes，Makefile引用camss-icp-hfi.c/camss-bps-cmd.c同tree缺失，IPE没列Makefile，所取c缺icp_get/ctxcreate/submit/destroy/abort定义。分支heads中仅一个名称含ICP/BPS/IPE；不能把此prototype当readydriver。upstream-sources/icp-reuse-assessment保留限定证据，不宣称所有仓库无实现。

352复用Realme原kernel git9668fcdc...（281同repo），定点10DT/A5/HFI文件131227bytes私存oem。SM8150 A5 ELF32加载，不是X1E MDT/PAS；5项CSRoffset不同：oldFW44/INIT48/RESP4c/SHMEM50/QTBL58 vsnew24/28/2c/30/38，doorbell旧30与新CIRQ124也不同。仅source契约，不盲写新SoC寄存器。

352手机只读vendor定点提取firmware/CAMERA_ICP.elf，3630392bytes SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63。private352/CAMERA_ICP.elf-private，ELF32 LE ARM ETEXEC entry0，3LOAD VA0/140000/340000，runtime span3686400，fits5MiBfirmwareIOVA窗口0..500000；要zeroBSS。当前DT camera/icp命名reserved-memory无节点，不等于动态分配不可能。ro/noload/noexec后已卸载/run/k352-icp-fw-ro，无NV/OTP/EEPROM/persist访问/安装文件变化/模块变化/重启/手机固件启动；原始数据只private。icp-firmware-collection passed。

352固件保留11688行symbols；arm-linux-gnueabi-objdump可用（不是aarch64objdump），ARM32 Thumb。完整HFI_QueueGetQHdr1a971..1aa10用privatek329venv Unicorn ARM/THUMB执行，30calls/1758instructions，三队列6排列*IDs0,1,2,3,255。表头24、qhdr956（字段每64byte间距前置60，尾padding60），start124/type188/qsize252/read828/write892；type低byte查找、fixedstride956，qsizeword*4后决定映射page4k/64k/1M。fakeCSR0xe0010058指QTBL；48tryMemMapping和30assert_loop成功桩，不实际IOMMU/固件boot。原firmware函数完整验证ABI，非图像处理已通。asm/symbols/cases只private，public firmware-queue-validation passed。

352无hostbuild/SDKbind/phonecamera worker；numerical工具/提取/ABI分析均保存镜像，353优先实际A5 HFI队列+ELF加载/映射后端，而非继续把不完整prototype当成可用驱动。随后IPE会话/IO+IQ/libcamera m2m，LTM核心/ADRC+frontCCM+Gamma，不能缩成CPU近似并当full完成。当前部署仍349最后观察338+r27/r22+344etc，348/349Gamma候选仍未安装，正常光学/AE防频闪/其它模式/多摄几何同步/连续AF等全目标未完成，goalactive。

'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：351','# 当前检查点：352',1);at=s.index('\n\n',s.index('\n\n')+2)+2;s=s[:at]+entry+s[at:];path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goalactive。读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel352/README。352新增LTM inverseGamma portable host/ARM31cases8060bytes0diff（原source非HAL），首版负delta signbit625bytes差已修并保留failed。已定点取得本机原厂CAMERA_ICP.elf私存kernel352（3.63MB、ELF32 ARM entry0、3LOAD runtime3.6864MB fits5MiBIOVA0），ro vendor卸载，无手机固件启动/模块/默认变化。原固件完整Thumb HFI_QueueGetQHdr30calls/1758instructions：qtbl24/qhdr956、type188/start124/qsize252按word、fixedstride，48mapping+30assert桩；非真实IOMMU/boot。ARM32 arm-linux-gnueabi-objdump/Unicornk329venv可用。BOD原型ebd1e440...只取9files，缺Makefile两实现且IPE没构建/API不全，X1E MDT/PAS/CSR不能套A5；已取同Realme9668源10个DT/A5/HFI。下一步353实际补A5 HFI queues+ELF加载/ICP SMMU映射后端，再IPE会话/IOIQ+libcamera m2m；别以CPU近似替代完整目标。351完整LTM149roots/2135regions及CCM43/737、front25矩阵/compiledflags已核；350Gamma全树与插值编码已核。deployed仍338+r27/r22+344etc；348/349Gamma已实测未安装。无活动worker/build/bind，所有firmware/vendor/table/asm/源私存，不镜像。完整AE/防频闪/模式/光学/同步/AF等仍待。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('352当前：LTM逆Gamma可移植实现通过主机/ARM对照，原厂ICP固件及实际队列ABI已恢复，继续补A5硬件后端；默认未改。[352详情](../../reference/kernel352/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150');paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths.extend(ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json'])
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded352 inverse-Gamma/ICP firmware/actual queue ABI progress; hardware backend pending; goal active.')
