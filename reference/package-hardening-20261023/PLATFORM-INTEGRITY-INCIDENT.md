# 平台签名包副本1误写事件

2026-10-23。这是本代理收尾脚本造成的交付错误，不是原构建失败，也不是未解释的文件系统损坏。

原两次独立构建在北京时间13:29产生同一个12387字节签名APK，SHA-256 `49c5b03456fab276f306d52127505190cffecc815fb2e7415aefae822cb05630`。13:57:09的收尾脚本先用变量p指向artifact-manifest.json，随后在“核对5个包”的循环中复用p指向每个APK，循环结束却执行p.write_text(manifest_json)。最后一个p正是platform-packages1的APK。之前的核对发生在误写之前，因而不能支撑“交付文件仍保持不变”的最终说法。

副本1实际变为artifact-manifest JSON：2301字节，SHA-256 `7e49e2f3e319f74ecea9c378f99705eb2e2c6f9bfe62e396769f0e03e98bac02`，APK验签/格式检查均失败，头部为JSON而非ADB。完整误写字节及mtime证据已保留；未通过改锁或重建掩盖差异。

已在核对移动源和目标绝对路径均留在私有package-hardening根后，将误写件移动到：

`E:/edk2-samurai-out/package-hardening-20261023/scratch-round3/platform-packages1-miswritten-artifact-manifest.invalid.json`

原platform-packages1目录不再有.apk，只留QUARANTINED.md及明确标记历史/invalid的manifest。**不能使用副本1。**

唯一保留的有效原始平台包：

`E:/edk2-samurai-out/package-hardening-20261023/platform-packages2/samurai-platform-5-r2.apk`

它仍为12387字节、SHA49c5b034…5630，mtime仍是13:29:03；未被覆盖或重建。真实APK验签成功后，只读解码其deflate APKv3数据块，逐份读取全部19文件的实际字节，核对签名目录中的hash/mode、原manifest以及两个原package() staging，全部一致。pulseaudio-bluez依赖存在，无安装脚本。具体19项结果见[核对报告](platform-integrity-incident.json)，原日志在私有integrity-incident-20261023目录。

公开artifact-manifest和README现在只引用副本2，明确区分“历史两构一致”与“当前仅1份有效”。本轮其它四个选定APK与既有hash一致；不能再笼统声称5份原包从未改变。未安装、未访问手机，没有修改充电、相机或公共平台源码。主线仍将独立核对最终交付。
