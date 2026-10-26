相机／骁龙ISP按用户要求暂停，先完成充电；本次仅文档与提交，不恢复设备/SDK/构建。先读NEXT及reference/kernel491/HANDOFF.md。未明确恢复前不申请相机窗口。

正式相机基线：484实装r33/r28，441三ISP KO＋468 sensor／四原厂profile；真实升级→r32/r27精确回退→再升级，3 native APK exit0。14例Gst256、RAW24、dual12，268IPE=242math+26bootstrap，实际/usr签名/UID/maps/lease过。

489 core b345af8b…8bdd仅两对象：487原厂属性＋488格式，485 Meson去RUNPATH。IPA6/签名/proxy/base/数学/KO/profile不变，ARM SDK加载/验签/路径解析过，未start CM/exec worker。490 r34/r29签名七包及精确r33回退、缓存solver过；491 package-only八例/强制恢复工具已离线验收及独审，未绑定/上传/实装，仅r1可用。

441/442主摄720/1080、469长焦720、474长焦1080同帧PD10/LTM因果复用。bootstrap单遍；新工具无硬件DC/pass计数。441积压失败未关闭，479控制SOF+2不外推全局delay。

手机归充电，当前boot/501进展以其最终记录为准。恢复须新boot/endpoint/guard/原钥及owner；核476旧363 pin，使用private481/formal-expected（1c458491…4705），不可套440或重放终态。WSL原guard/32GiB留2GiB；原厂/样本私存，selected脱敏。光学/AF/录像/热/多摄/第五未完。
