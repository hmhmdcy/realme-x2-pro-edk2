# PipeWire公共相机缓冲修复配方

PipeWire1.6.9-r3，基于Alpine aports固定提交0afac626498565714f7a06c04589112584cc95f4的完整官方APKBUILD与辅助文件。归档固定GitHub1.6.9 tar的名称与摘要，详见[source-lock](source-lock.json)。

保留上游systemd补丁，并顺序追加六个项目补丁：

1. Gst延后unref的上游锁顺序修复。
2. 保留可选复制诊断功能，默认关闭；生产启动项不启用。
3. 核心可靠广播、远端代理重协商与绑定IO生命周期。
4. SPA Busy引用、延迟复用、IO初始化及图退役后的新图像分配。
5. 公共映射范围查询，支持没有默认映射的真实导入块。
6. Gst共享帧的独立Busy引用/元数据映射与所有权诊断。

SPA自动声明可靠广播，标准客户端共用修复。SPA与Gst子包均精确依赖同版本core；应用不需要复制开关或私人库路径。新增引用不逐帧复制像素或清零Busy计数。

精确原始tar的12项source SHA512、7个补丁零fuzz应用、shell语法及7个编译输入与部署源码一致。[核验](../../../reference/kernel265/recipe-prepare-validation.json)。**完整abuild尚未执行**；不能写成全部子包重建或全新rootfs通过。

实机为三个原生可信签名APK：SDK增量源码编译后保留当前可信载荷，完整文件表校验，其余42个普通文件与一个符号链接保持，替换三个ELF。仅三个包记录变化，仍961包；core/SPA r2与Gst r1的联合回退包保留并模拟通过。[包与ABI](../../../reference/kernel265/package-build-validation.json)、[事务](../../../reference/kernel265/package-install-validation.json)。

组合候选3201次、原生系统2972次保留前缀检查无内容/PTS变化或回收错误；原生前后摄6张照片及实际Snapshot前摄窗口快门通过。检查限定每帧前65536字节。单独Gst/SPA与旧临时引用候选的失败保留；画质、GUI切换、其它后摄、GPU和完整适配继续开放。[完整结果与限制](../../../reference/kernel265/README.md)。
