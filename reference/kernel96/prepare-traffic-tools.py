from pathlib import Path
import subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel96');out=Path('/mnt/e/edk2-samurai-out/kernel96')
source=(ref.parent/'kernel92/wifi-traffic-server.c').read_text().replace('htons(18092)','htons(18096)')
source=source.replace('if (argc != 2 || inet_pton','if (argc != 3 || inet_pton')
anchor='    umask(077);\n'
replacement='''    const char *phase=argv[2];
    if (strcmp(phase,"initial") && strcmp(phase,"recovery") && strcmp(phase,"five-ghz")) return 2;
    char tx_path[100],rx_path[100];
    snprintf(tx_path,sizeof(tx_path),"/tmp/k96-%s-traffic.bin",phase);
    snprintf(rx_path,sizeof(rx_path),"/tmp/k96-%s-traffic-upload.bin",phase);
    umask(077);
'''
assert source.count(anchor)==1;source=source.replace(anchor,replacement)
source=source.replace('upload ? "/tmp/k92-traffic-upload.bin" : "/tmp/k92-traffic.bin"','upload ? rx_path : tx_path')
(ref/'wifi-traffic-server.c').write_text(source)
target=out/'wifi-traffic-server';assert not target.exists()
subprocess.run(['aarch64-linux-gnu-gcc','-O2','-D_GNU_SOURCE','-Wall','-Wextra','-Werror','-static',str(ref/'wifi-traffic-server.c'),'-o',str(target)],check=True)
source=(ref.parent/'kernel92/wifi-traffic-client.ps1').read_text()
source=source.replace('$client.Connect($remoteAddress, 18092)','$connect = $client.ConnectAsync($remoteAddress, 18096)\n        if (!$connect.Wait(10000)) { throw "Wi-Fi TCP connect timed out" }')
(ref/'wifi-traffic-client.ps1').write_text(source)
print('Phase-specific bounded RAM traffic tools prepared')
