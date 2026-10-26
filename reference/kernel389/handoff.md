# 当前检查点：389（正式 CAMSS/ICP 部署候选，目标active）

先读WORKING-BOUNDARIES.md、reference/kernel389/README.md。388交接归档archive/NEXT-SESSION-through388-2026-10-21.md。本轮是实质源码／构建／部署候选进展，没有设备状态切换。完整目标仍active；用户关灯条件继续，黑／噪点不单独判故障。

## 当前源码与产物

WSL Ubuntu root，任何源码/build访问先reference/kernel284/storage.py::mounted_build()，持久ext4 /mnt/samurai-full282；绝不格式化／重建32GiB backing。source354分支samurai-icp-platform389，HEAD a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07，干净，父38895caf30a629bbaf454ebfc9ed25ce16ea3a952b5。source-state.json、platform-and-board.patch为最终，verify-source已核对源/proposed/父提交patch。实际模块r4源fcaf366...，最终只修YAML pattern；DTB源bdce399...，DTS后续未改。

新增camss-icp-platform.c，匹配qcom,sm8150-camss-icp，不含overlay／测试参数／固件RAM读取；probe不请求固件或释放CPU。正常CAMSS与ICP同一个qcom-camss模块所有者，注册CAMSS→ICP、退出逆序。IPE contexts/exports/retained DMA因此同时保留共享CPAS供应者；两driver suppress_bind_attrs，静态设备，不声称任意热拔插。PM回调复用core，系统挂起委托runtime PM，backing忙时拒绝断电。

m2m bound回调改bool(struct device*)，正式路径用device_is_bound，旧test回调也已适配。允许NULL owner供built-in；owner_refs对NULL安全。模块态真实Kconfig选ICP=y、CAMSS/core/m2m=m；26例provider覆盖module/builtin参数，未构建完整builtin vmlinux。owner_refs如今是整个qcom-camss的引用数，PW/WP打开普通相机也计数；不能当导出buf数，停桌面服务后再判断0。

private=/mnt/e/edk2-samurai-out/kernel389。*-intree-r4.ko：qcom-camss2838304B/SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288；adapter118944B/SHAa0167f6acce4edad159d43101a723846ed494cf71fe3bb27857d2d145b44a7b8。core350472B/SHA036f590...，helper/SG及其它4vb2均与388二进制一致。标准SG含388新增owner导出符号，旧SG不能加载新adapter/CAMSS。现有v4l2-isp与新产物全哈希不同，但.text/.rodata完全一样，保留现有ISP模块。11目标W1/-Werror无诊断，build相关目录/config/symvers均恢复。所有build exec会话已终态。

SoC DTS完整7SID但默认disabled；Samurai候选status=okay，firmware-name=qcom/sm8150/camera-icp.elf，原camera_mem9ab00000/5MiB/no-map不变，加入五个仅iommu-addresses的保留节点，未新增物理RAM。DTB samurai389-private.dtb115927B/SHA0cc9dfd29044d7ca9ed2dbadbb62cedacd0298eba23fce377112ffe70d3b5db7；970个变化引用单元目标路径保持，其余属性语义不变。dtschema2026.9验证新binding及实际DTB，四个负例拒绝；本地binding草案未上游评审。验证范围不外推全板binding。

EDK2真实载体boot-partition-k389-icp-platform.img100663296B/SHAe0256ff5bad0f6a2139de8690974d5fc25a0b58cad4cec1bb22f26bf0280884f。与boot366逐FFS比较仅DT模块变，其它固件代码/数据、shim/ramdisk/Android头/compat/尾部不变；30个既有诊断模板，无新增。仓库DT及3个共享固件输出恢复。回退boot366私有原件SHAc3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924。

## 下一步：实际部署与回归

部署清单deployment-manifest-private.json、完整deployment-bundle-private.tar.gz已生成／成员重核；含boot、5模块、原厂ELF，未上传。完整包约24MB，不通过短超时SSH stdin整包上传。modules-firmware-private.tar.gz是分离的小包，module-stage-manifest-private.json带boot摘要关联；boot继续复用原本本地fastboot流程。prepare-package.py和prepare-module-payload.py非幂等，已有产物先查，不要重跑覆盖。

先核对实际boot和模块文件存在/缺失、initramfs是否包含旧相机模块、原依赖和原文件离线回退，再设计守护事务：精确5模块(CAMSS/core/adapter/helper/SG)＋原厂ELF＋depmod，正式DT载体；保留Image363、logdump365、已安装r29/r24，不重装全部778模块。参考366/build-boot.py、prepare-deployment.py/flash-boot.py的验证流程，但必须用现在378guard及boot366回退，不能直接运行旧guard旧rollback脚本。

手机未改：同一378恢复boot，host389→388→378→371→360原USB SSH key/known_hosts；guard /var/lib/samurai/k378-recovered/boot-id-private.txt。current-state只读核对原CAMSS/SG文件和loaded-note一致、候选模块/正式FW不存在、静态ICPdisabled、taint0、CAMSS双CCI suspended。Image363/boot366/DT365、五包r29/config-stack r24和362私有Preview仍在；SSC旧EPERM/daemon4/SLPI offline未修，勿盲重试DSP。389无后台设备worker。

启用后检查真正icp@ac10000正常driver绑定、无test模块和临时overlay，再验证导出FD/mmap保留共享owner、原生像素、四摄libcamera/主摄RAW/隔离IPA、已安装IFE路径和恢复。libcamera继续先复用387私有候选，SHA60181b3cd025febfeb1812996bc63aaa53721a47ba45bd6ef1d3f92596329c3d；正式用户空间包后续落地。389没有正式driver实机帧，不把388的99 direct/0copy/0cancel/0failed移作389证明。

## 审计与完整范围

r1属性组命名编译错已修；r2 modpost漏v4l2-isp构建目标已补；r3通过后加空固件名检查，最终r4通过。DT核对器补齐hwlocks/resets/GPIO等已有引用属性后逐单元核对，没有允许其它属性变化。schema标准路径修正，minLength换合法pattern；26模型／4负例通过。失败均未上机。

388直接DMA的DMA-only SG与自有IOMMU域物理重叠校验、未知完成保留DMA、A5/IRQ+IPE resetACK后释放仍有效；显式V4L2所有权，不声称完整implicit-fence发布互操作。继续正式部署、在途取消/硬件错误并发，原厂Gamma/LTM/CCM完整IQ，以及363/REMAINING-CAMERA-SCOPE.md全部：第五2MP、多模式、动态帧时长/防频闪、几何/多摄同步、连续AF。383 Unicorn全局MEM_READ破坏ThumbIT/SP陷阱，373/375/376/379、381、377/378失败审计保留。

FW/HAL/汇编/CDM/日志/图像/个体校准仅private。公共mirror /home/cy122/edk2-samurai/repo的Platform/Realme/sm8150，只本地提交，不push/PR，保留其它改动。
