# IMX471原生尺寸Quad Bayer实验补丁

0001-libcamera-imx471-native-quad-cpu.patch已作为0011加入完整r6配方，两份补丁逐字一致。原始算法与400组独立参考检查见[218记录](../../../../reference/kernel218/README.md)，完整包实机验证见[219记录](../../../../reference/kernel219/README.md)。

实现保留原生4608×3456尺寸，明确实验配置才开启，默认关闭。219完整r6库重新通过50组/780,337,408像素的CPU类合成测试，真实传感器完整RAW及CPU RGB也各取得六帧，包含暗场与图案正对照。

内部TPG在完整模式按普通Bayer周期生成，因此RGB图案仅证明尺寸/传输/分配与非黑输出。真实场景标准CFA/几何、颜色/标定和日用画质仍未验；RAW传感器约30fps不代表CPU RGB可实时30fps。完整模式模块参数与用户态实验选项均默认关闭。[图案边界](../../../../reference/kernel219/test-pattern-layout-notes.md)。
