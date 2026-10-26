# 453：BU64253 标准镜头驱动候选

2026-10-23。由[450离线模组核对](../kernel450/LENS-SCOPE-NEXT.md)得到的底层增量。**已按原Image363配置／ABI独立编出真实in-tree模块，并执行原C固件解析／初始化的宿主ASAN／UBSAN检查；DT定向依赖检查通过，卸载生命周期及PM错误路径仍需修正／验证，未部署。**未改共享source354／build或当前 libcamera 候选，未使用手机／SDK。

[bu64253.c](bu64253.c)复用本项目274／276已经运行的标准 V4L2 lens、单一 VDD 消费者、open/close runtime PM 结构；替换为已恢复的10bit命令。其它镜头不会复用主摄0x84协议、0xe0初始化或100ms掉电规则。短写／NACK以错误返回；供电关闭失败保留引用，初始化失败尝试释放VDD，未确认的ID、位置读回、park和待机命令均未添加。

两模组硬件初始化通过独立私有文件接入，驱动没有猜测D0位域名称或把某个sensor型号写入控制算法。[DT草稿](samurai-bu64253-lenses.dtsi)描述原厂已核的CCI／VAF／`lens-focus`，不改sensor或SoC成像代码；[binding草稿](rohm,bu64253.yaml)中的固件接口需要在集成前审查。首次只接一颗镜头；文件未被任何生产DTS包含。

私有格式 `BU53 v1`：8字节头部（`BU53`、version1、count3、两字节reserved0），随后三条4字节 `<address8, value8, delay16le>`。仅允许原厂已核的D0／C8／F0顺序、两种已知D0值和5／100／10µs延时。缺文件、格式／版本／长度／命令非法时 probe 在任何VDD使能和I2C写之前失败。文件由现存BIN加独立XML生成，保留SHA来源，原件不公开：

| 模组 | 私有输出／安装相对名 | SHA256 |
| --- | --- | --- |
| IMX319 | `E:/edk2-samurai-out/kernel453/imx319-bu64253-init.bin` → `camera/realme-x2-pro/imx319-bu64253-init.bin` | `10214cf01b93f146602854f2141561a45a87925856c5b1c64380095ce90f55e9` |
| S5K3M5SX | `E:/edk2-samurai-out/kernel453/s5k3m5sx-bu64253-init.bin` → `camera/realme-x2-pro/s5k3m5sx-bu64253-init.bin` | `e99297e0be59e0f554fc3e3e3883c8d356c72f18b09def8563281ac119923fab` |

初始化文件只有硬件命令，不含初始焦点、EEPROM端点或距离映射。打开节点只初始化芯片，不任意选择DAC；仅显式成功控制的目标可在随后resume重用。各自原厂默认范围见私有候选及来源指纹，需与当前模组及个体AF数据区别对待。驱动0…1023是协议范围，宿主遍历编码没有对应任何物理镜头动作。

还需数据层接入：当前硬件IPA只有在 `autofocus.lens` 与实际 `CameraLens::model()` 一致、且驱动控制范围通过检查时才声明 AfMode。加入驱动／DT不会自动补齐这项；两份私有模组配置应另加 `lens: bu64253` 和经确认的搜索参数，不能复用主摄 `lc898219xi` 行程、稳定时间或距离映射。本轮未生成未经验证的AF配置。

[原始契约检查](check-wire-contract.py)验证281原厂ELF的实际指令字与WRITE_DAC_VALUE跳表，解出MOVZ／AND／BFM位域，与候选C源中的两个实际算术表达式逐一比较全部1024个合法DAC；两份初始化按独立XML交叉核对。[该次收据](wire-contract-validation.json)仅覆盖数学表达式、数据格式和静态调用顺序，真正C执行与内核编译见下。

[原C检查](check-init-c.py)从当前驱动逐字提取loader、probe、resume及写表等7个函数，以宿主桩执行，ASAN／UBSAN通过。两份有效FW、18类缺文件／非法格式、缺属性和加载I/O失败两例均实测；失败前VDD查询、PM注册、上电及I2C计数全零，未验证配置的resume也直接拒绝。有效resume只发对应三条初始化，不写任意默认DAC；三条初始化分别注入短写／NACK，共6例均退电并保留原错误。[C收据](init-c-validation.json)。这覆盖实际C逻辑，仍不等于Linux PM框架、真实总线或供电故障实测。首个宿主桩编译曾因误导缩进被Werror拒绝，仅修桩后通过，r0日志私存；生产驱动未因此改动。

[模块构建](build-module.py)先从保留Image363提取内嵌`.config`，SHA `23e088a9…f30ed`逐字节等于363构建记录；输入Module.symvers同样匹配原Image363的`0837fdc3…9223`。使用独立`kernel453-lens-private/source-view`与`O`，只准备私有生成头并构建`drivers/media/i2c/bu64253.ko`，不构建Image／rootfs。首轮准备及模块共20.98秒，当前r2复用私有准备后的单模块目标4.34秒；W=1／KCFLAGS=-Werror零诊断，真正intree=Y、74264字节、SHA `ba5ad180…14c4b`，vermagic精确k363，33个导入均存在于原363符号表。当前源码SHA `7eaba1a2…f4351`与模块／原C／编码收据一致；更新头部状态注释未改七个实际函数体。私有olddefconfig只新增一个CAMSS选项的禁用记录，相关共享源、配置、生成头和符号表保持。[模块收据](module-build-validation.json)。模块与完整日志仅在`E:/edk2-samurai-out/kernel453`；没有加载模块或修改DT。

后续[DT检查](schema-validation.json)中baseline／候选实际编译、251处显式phandle及lens／PM8008／CCI／两sensor共5组定向依赖通过；没有删节点，只新增两lens和两VAF并挂lens-focus。公开binding仍缺真实maintainer元数据，私有placeholder仅验证结构，不代表可提交的binding。真实内核PM／硬件未因此验收。

[框架反例](schema-pm-proof.json)从实际v4l2_subdev_release逐字提取：允许release回调释放sd后仍写sd->devnode，宿主ASAN复现UAF；前移清空后ASAN／UBSAN通过，真实内核尚未改。镜头自身还需避免devm对象在持有subdev FD时unbind过早释放，以及VDD disable失败后remove进入regulator_put的引用问题。resume初始化失败与suspend关闭失败的runtime_error行为不同，不能用宿主直接回调测试替代真实PM框架。完成这些生命周期条件后才启用lens。

[AF来源](AF-PROFILE-NEXT.md)已按固定原厂schema完整解码39份root并与原厂XML逐字段相等，8次模式管理器绑定一致；实际HAL nominal index→DAC核心逐项复现。两模组分区步距、阶段帧策略、阻尼及候选全部私存；当前均匀DAC步距／固定ms稳定时间／FoM域尚不能直接消费原件，EEPROM个体checksum／margin／姿态未核，候选不可部署。

接续顺序：先收敛框架／driver生命周期，再准备私有FW并验证可加载，之后只启用一颗lens。`lens-focus`会建立sensor async依赖，lens probe失败可能使原本可用的sensor不注册，必须保留当前DT／模块回退；不假定能直接用overlay替换已注册sensor。

后续[455寿命候选](../kernel455/README.md)已完成真实 in-tree 模块和42个原C宿主案例，补入 kref、晚 close、上电前模块引用及 VDD 失败隔离，仍依赖0064 core进入实际内核；没有部署或覆盖453历史。它保留故障对象的策略不能写成全部资源释放或实际PM并发已验收。

[个体AF分支](AF-INDIVIDUAL-NEXT.md)进一步执行当前281原厂HAL的EEPROM格式化、margin／clip／重建步表及姿态数值核心，软件交叉验证通过。但外部 OemCamActuatorSettingMap override、checksum接受条件及实时姿态门槛仍未知，条件候选不可部署；未把旧vendor配置或 nominal 步表冒充本机最终个体AF数据。

实机先只读核对适配器、现有媒体图、VAF资源与缓存模组对应关系；BU64253尚无已确认的可读chip-ID寄存器，不能盲读或全总线扫描冒充识别。驱动就绪后用标准接口查询控制，再按原厂约束做一次常规AF，验证光学响应／FoM和停流释放，保留身份和个体端点未知。未确认供电电气最小间隔；10ms上电后等待和1ms关闭后等待只复用原厂序列。缺FW、非法FW、总线／供电错误与常驻CameraManager的枚举及停流PM必须在集成验证中覆盖。

[下次限定补取](AF-EXTRACTION-NEXT.md)已核281的真实来源为手机当时的vendor分区；采后已卸载，不假定当前仍挂载。下一串行窗口先读当前节点／格式／挂载和完整HAL指纹，精确匹配后再取单个配置库；不需下载整份ROM或重采EEPROM。尚未访问设备或补得库。
