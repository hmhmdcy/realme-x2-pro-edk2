该APKBUILD仅封装已有207可信二进制，保留字节，不重新编译。二进制输入和完整配方输入位于私有输出的tftp-abuild-inputs；公开保存配方及与签名构建器相同的采用钩子。source-lock固定源码重建依据，源码构建仍用linux-port/radio/build-tftp.py。abuild路径尚未执行；实际已验签APK由../build-tftp-apk.py产生。设备文件owner和精确替代关系尚待当前设备窗口核对，未批准安装。

第二轮确认APK3脚本失败仍可提交文件/DB。钩子仅advisory，外部APK前置校验是唯一推荐安装入口；本目录草案不能被当作失败即阻断的安装方案。已签名旧包保持不变。
