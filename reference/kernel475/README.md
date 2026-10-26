# 475：r33／r28 可回退候选物料，未安装手机

已生成并签名七个运行 APK、前进／当前正式版本回退索引，以及四模块／四原厂配置的私有载荷。**包管理器升级／降级尚未验证通过**：缓存 rootfs 严格安装 r32 基线时缺少依赖，尚未进入 r33。独立 SDK 环境中的包内默认 loader、六个 IPA 签名和文件往返检查通过；这是载荷检查，不是包数据库事务或手机部署证明。

## 具体版本和可复现入口

[package-cohort.py](package-cohort.py)复用现成二进制生成 `libcamera`、`libcamera-ipa`、`libcamera-tools`、`libcamera-gstreamer`、`libcamera-v4l2` 的 `99990.7.2-r33`，以及 config／stack `0.1.0-r28`。七包和两个索引均用既有签名输入签名并严格验证，未重建 libcamera、Image 或模块，也没有 `allow-untrusted`。[七包清单与依赖](package-r1-validation.json)。

回退七包逐字节复用当前正式 [440](../kernel440/README.md) 的 r32／r27，未取其旧 r31 回退。GST／tools／v4l2 和通用配置的载荷字节保持，仅更新版本与必要精确依赖；IPA6 及其它相关运行子包显式绑定 r33 core，stack 固定全部七包。这里只生成已安装范围的七个 runtime 包，没有将旧十三个完整功能子包全部升版的声明。

| 新包内文件 | 精确来源／SHA256 |
| --- | --- |
| core | 473；`a21fcedde2f591f809a9c388a9a6ab78fa5072f33e06c91bbd55c8abf34cd97b` |
| base | 461 可复用 output；`f8c3039b31a18007b8ccb920493b010a3629113f30d151a8820f68c0b845f3c4` |
| CAMSS proxy | 451；`35526054954ce43d1068c710f6be6d4cd172288e4da7ffcab677712815f08f4d` |
| CAMSS IPA6 | 444；`4c90047d42a91b9b1585d3b2cda997d8eee61f5e3a20f136b4345abcc2556d39` |
| 原 IPA6 签名 | 444；`f5c351bd947363791c072a7b9916adea00ec1a02c52671d7f9692aa735386205` |

为保留已实测组合的精确字节，本轮没有 strip 或去 RUNPATH。实际 core RUNPATH 为 `$ORIGIN/base:/`，proxy／IPA 为 ORIGIN 相对库路径；没有空项或相对当前目录搜索，core 仍含绝对 `/` 搜索项。debug、体积及这些 RUNPATH 是正式化边界，不能把本候选称为最终精简发布。

[prepare-source-recipe.py](prepare-source-recipe.py)生成明确的[0066 增量](0066-camss-r33-processed-ipe-cohort.patch)及 [r33 配方](recipes/libcamera/APKBUILD)、[r28 配方](recipes/samurai-camera-config/APKBUILD)。从实际440源码重放12个改动文件，零 fuzz／offset，分别与473 core 源和451 worker serializer 源逐字节相同；0065所有权修复和448 helper均保留。[源码收据](source-recipe-validation.json)。脚本在475私有目录用440现有配方材料拼成完整配方入口；本轮没有执行该全量配方构建，实际 APK 由上述受哈希约束的 snapshot 打包入口产生。

## 四模块、四配置与权限

[私有物料清单](private-payload-validation.json)列出四模块、四profile的前进／回退文件哈希、note及目标路径。前进为441 CAMSS／ICP core／m2m和468 S5K3M5；回退为434三模块和正式 S5K3M5 `966b29d8…`。旧 sensor 从已核对 SHA `fca01dab…` 的363原模块归档单独提取，47744字节，与468／474的正式恢复基线匹配；没有冒用共享 build 中不同哈希的模块。

原厂配置仅在私有载荷：主摄443补齐原厂 mode4 DS4；长焦468保留原mode3并新增原厂mode2；广角、前摄沿用440。回退四份均为440原件。通用默认配置和管线默认640×480／RAW原生策略保留，未加入新的640×480／RAW实机验收声明；新包及完整四摄光学、AF、录像／热条件仍待验证。组件的同帧与1080p LTM实机证据单独见[474](../kernel474/README.md)，不当作本包已安装。

最初只用363 symvers加四候选导出检查 imports，漏掉既有 V4L2 provider，失败原件保留；此静态方法不完整，不能由此断言模块 ABI 不兼容，也不能把它修饰成通过。物料按精确 KO 哈希绑定既有441／468构建和474实际加载／恢复证据，没有重建 provider 或改变兼容前提；`CONFIG_MODVERSIONS`关闭也不提供额外CRC证明。

最终传输归档为私有 `cohort-r2-private.tar.gz`，28,547,778字节，SHA256 `0875d5a9e56ef5b74cba39f47df8d2e3bfeb2290113e1c6630d6f777c01b62c3`。[r2归档收据](private-archive-r2-validation.json)核对32个非manifest成员字节与r1相同；manifest只增加明确的权限合同。r1继承DrvFS的1000:1000／0777 header，已保留原观察；r2全部为root:root、私有staging目录0700／文件0600。

**解包只是私有暂存，不是安装。** 未来系统安装须显式root:root、目录0755、KO／profile及仓库文件0644；APK文件按各自签名ACL安装，不保留DrvFS owner／mode或直接将staging权限当系统权限。切换必须先停止客户端和PW／WP、证明无live camera FD及所有权idle，先卸CAMSS再换sensor；恢复时先恢复原sensor，再恢复匹配434模块、r32／r27与四配置。world、仓库入口、服务环境和原文件属性须由新的设备事务备份恢复；本轮没有执行这个设备事务。

## 安装失败和独立 loader 的证据范围

[APK root结果](apk-root-validation.json)保留明确失败。初次SDK私有overlay在包事务前拒绝40个PMOS本地旧签名缓存；其信任集补用缓存rootfs的现有公共key后，仍缺两把 `pmos@local` 旧公钥，没有忽略签名。新r2改用保存的**缓存rootfs目录**作只读lower，仅295个可信缓存进依赖索引，严格solver在安装r32时返回8：缺 `libgstallocators-1.0.so.0`、`libgstbase-1.0.so.0`、`libgstreamer-1.0.so.0`、`libgstvideo-1.0.so.0`、`libgtest.so.1.18.0`。r33升级和数据库回退均未发生；没有伪造数据库、改依赖或继续扩包。

目标充电侧串行只读 `apk --version` 原件确认 aarch64 `3.0.8-r0`，与隔离工具一致；缓存rootfs APK SHA为 `9f86d52a…`。生成的是 APK v3／ADB 格式，实际 verify／解码和签名索引通过；同版格式证据不等于已在手机安装。旧三次安装前失败、各信任集来源及最终solver失败均保留；缓存rootfs不是当前手机完整根文件系统的替身。

[独立 loader结果](payload-loader-validation.json)使用已有SDK依赖，实际解码签名 APK 到空prefix后逐文件核对并复制到私有overlay。默认 `cam`／`lc-compliance` help、musl loader、core／base／GST／v4l2／IPA五个DSO的RTLD_NOW和六个IPA签名通过；随后恢复r32载荷及四KO／四profile文件的字节与目标属性。它没有APK数据库／依赖事务语义，不能称“安装升级／降级通过”。第一次直接向已有文件树extract发生File exists，旧失败保留，后续使用空prefix修正了检查方式。

所有host过程已终态，overlay均卸载，SDK无bind且已释放，SDK及缓存rootfs的db／world保持。原厂系数、模块、APK和完整日志只在私有475；签名秘密沿用原有私有位置，未复制或公开。未访问手机／USB／PM／SSH，未改共享source／O、NAV或Git index。[最终物料状态与文件哈希](candidate-state.json)。下一设备窗口可用目标当前真实provider做只读solver验证，再决定是否推进新安装事务；不用为本地缓存缺项修改依赖。
