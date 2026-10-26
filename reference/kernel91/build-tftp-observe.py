from pathlib import Path
import hashlib,subprocess
O=Path('/mnt/e/edk2-samurai-out/kernel91')
B=O.parent/'kernel88'
R=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel88')
s=(B/'tqftpserv/tqftpserv.c').read_text()
old='\t(void)buf;\n\t(void)len;\n\tlog_err("WRQ denied: firmware service is read-only\\n");'
assert s.count(old)==1
s=s.replace(old,'''\tstatic unsigned count;
\tif (len <= 2) return;
\tsize_t n = strnlen(buf + 2, len - 2);
\tif (n == len - 2) return;
\tif (count++ < 20)
\t\tlog_err("WRQ observed and denied: %.*s\\n", (int)n, buf + 2);
''')
(O/'tqftpserv-ro-observe.c').write_text(s)
s=s.replace('int main(int argc, char **argv)\n{','int main(int argc, char **argv)\n{\n\tsetvbuf(stdout, NULL, _IOLBF, 0);')
(O/'tqftpserv-ro-observe.c').write_text(s)
subprocess.run(['aarch64-linux-gnu-gcc','-D_GNU_SOURCE','-O2','-static','-I'+str(B/'qrtr/include'),'-I'+str(B/'tqftpserv'),str(O/'tqftpserv-ro-observe.c'),str(B/'tqftpserv/translate.c'),str(B/'qrtr/lib/qrtr.c'),str(B/'qrtr/lib/logging.c'),str(R/'ro-firmware.c'),'-o',str(O/'tqftpserv-ro-observe')],check=True)
print(hashlib.sha256((O/'tqftpserv-ro-observe').read_bytes()).hexdigest())
