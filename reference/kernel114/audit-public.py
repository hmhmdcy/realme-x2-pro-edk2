from pathlib import Path
import re

root=Path('/mnt/e/RealmeX2Pro edk2')
source=(root/'reference/kernel113/audit-public.py').read_text()
source=source.replace("'sessions/113-sensor-power-and-extended-rpc.md']]", "'sessions/113-sensor-power-and-extended-rpc.md', 'sessions/114-complete-rootfs-and-qmi-ipa-foundation.md']]")
source=source.replace('for stage in (109, 110, 111, 112, 113):','for stage in (109, 110, 111, 112, 113, 114):')
source=source.replace("root / 'reference/kernel113/public-audit.json'", "root / 'reference/kernel114/public-audit.json'")
assert '114):' in source
exec(compile(source, str(root/'reference/kernel113/audit-public.py'), 'exec'))
hardware=(root/'linux-port/docs/HARDWARE-STATUS.md').read_text()
assert len(re.findall(r'^\| (?:触摸|原生显示面板|GPU|普通USB与OTG|Wi-Fi|蓝牙|NFC|音频|电池与充电|蜂窝网络/数据|摄像头|其它传感器|指纹|振动|GNSS定位) \|',hardware,re.M))==15
assert '新本机专用F2FS sparse rootfs已生成' in (root/'README.md').read_text()
assert '镜像没有刷入' in (root/'NEXT-SESSION.md').read_text()
print('STAGE114_CURRENT_DOCS_AND_PRIVACY_BOUNDARIES_PASS')
