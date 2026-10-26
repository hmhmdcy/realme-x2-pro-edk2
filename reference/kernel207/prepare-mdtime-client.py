from pathlib import Path
import host, shutil, subprocess
here = Path(__file__).resolve().parent
path = here / 'test-tftp-qrtr.c'
shutil.copyfile(path, host.PRIVATE / 'native-client-source-before-mdtime-private.c')
source = path.read_text(); needle = '    if (!strcmp(argv[2], "deny")) {'
assert source.count(needle) == 1
source = source.replace(needle, '''    if (!strcmp(argv[2], "read-mdtime")) {
        const char *local = "/run/samurai-wifi/firmware/qcom/sm8150/realme/samurai/modem_pr/mcfg/configs/mcfg_sw/mdtime.txt";
        FILE *f = fopen(local, "rb"); assert(f);
        size_t count = fread(data, 1, sizeof(data), f); assert(!ferror(f) && feof(f)); fclose(f);
        read_file("/readonly/firmware/image/modem_pr/mcfg/configs/mcfg_sw/mdtime.txt", data, count, 512, 1, 0, 1, 0);
    } else if (!strcmp(argv[2], "deny")) {''')
path.write_text(source)
base = host.PRIVATE.parent / 'kernel206/tftp-clean-rebuild-r2/qrtr'
binary = host.PRIVATE / 'block-rollover/native-client-with-mcfg'
p = subprocess.run(['aarch64-linux-gnu-gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-I' + str(base / 'include'), str(path), str(base / 'lib/qrtr.c'), str(base / 'lib/logging.c'), '-o', str(binary)], capture_output=True)
(host.PRIVATE / 'block-rollover/mdtime-client-build.log').write_bytes(p.stdout + p.stderr)
assert p.returncode == 0 and not p.stderr
host.upload(binary, '/var/lib/samurai/k207-mcfg-stage/native-readonly-client')
host.ssh('chmod 700 /var/lib/samurai/k207-mcfg-stage/native-readonly-client')
print('Read-only native QRTR mdtime client staged; no source payload is printed.')
