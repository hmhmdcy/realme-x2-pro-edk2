"""Build the RAM work-file server from the previously deployed TFTP source."""
from pathlib import Path
import difflib, hashlib, json, subprocess
here = Path(__file__).resolve().parent
repo = here.parents[1]
out = Path('/mnt/e/edk2-samurai-out/kernel206/tftp-build-r5')
out.mkdir(mode=0o700)
base = out.parent.parent / 'kernel88'
before = (out.parent.parent / 'kernel91/tqftpserv-ram-probe.c').read_text()
assert 'tsize > 4096' in before and 'pos > 4096' in before
source = before.replace('seek != 0 || tsize > 4096', 'seek < 0 || seek > 8388608 || tsize > 8388608 - seek')
source = source.replace('blksize > 65535 || wsize > 128', 'blksize < 8 || blksize > 65535 || !wsize || wsize > 128')
source = source.replace('RAM probe limits', 'RAM work-file limits').replace('RAM probe limit', 'RAM work-file limit')
source = source.replace('translate_open(filename, O_WRONLY | O_CREAT)', 'translate_open(filename, O_WRONLY | O_CREAT | (seek == 0 ? O_TRUNC : 0))')
start = source.index('static void handle_wrq(')
anchor = '\tsock = qrtr_open(0);'
at = source.index(anchor, start)
source = source[:at] + '''\tif (lseek(fd, seek, SEEK_SET) < 0) {
\t\tclose(fd);
\t\ttftp_send_error_to(sq, TFTP_ERROR_EACCESS, "Invalid work-file offset");
\t\treturn;
\t}

''' + source[at:]
source = source.replace('pos > 4096 || client->blk_offset > 4096 - (size_t)pos', 'pos > 8388608 || client->blk_offset > 8388608 - (size_t)pos')
source = source.replace('send_len > p - buf', 'send_len > (size_t)(p - buf)').replace('tsize && *tsize != -1', 'tsize && *tsize != (size_t)-1')
# The old probe's reader treats omitted rsize (zero) as a zero-length limit.
# Track the short final DATA packet and cap a requested range before sending.
source = source.replace('\tuint16_t blk_expected;','\tuint16_t blk_expected;\n\tbool read_eof;')
start = source.index('\t/* If rsize was set, we should limit')
end = source.index('\n\tlog_debug("Sending %zd bytes', start)
source = source[:start] + '''\tif (client->rsize) {
\t\tsize_t relative = offset - (size_t)client->seek;
\t\tsize_t remaining = relative < client->rsize ? client->rsize - relative : 0;
\t\tresponse_size = remaining < (size_t)len ? remaining : (size_t)len;
\t\tsend_len = 4 + response_size;
\t} else {
\t\tsend_len = p - buf;
\t}
\tclient->read_eof = send_len < client->blksize + 4;
''' + source[end:]
source = source.replace('if (last * client->blksize > client->rsize)', 'if (client->read_eof)')
source = source.replace('if ((block + 1) * client->blksize > client->rsize)', 'if (client->rsize && (block + 1) * client->blksize > client->rsize)')
source = source.replace('if (n == 0)\n\t\t\tbreak;', 'if (client->read_eof)\n\t\t\tbreak;')
# RRQ uses the same bounded transfer buffer as WRQ.
start = source.index('static void handle_rrq(')
at = source.index('\tsock = qrtr_open(0);', start)
source = source[:at] + '''\tif (blksize < 8 || blksize > 65535 || !wsize || wsize > 128 || blksize * wsize > 1048576) {
\t\ttftp_send_error_to(sq, TFTP_ERROR_EACCESS, "Read transfer limits");
\t\treturn;
\t}

''' + source[at:]
assert source != before and 'tsize > 4096' not in source and 'pos > 4096' not in source
(out / 'tqftpserv.c').write_text(source)
(here / 'tqftpserv-work-files.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True), source.splitlines(True), fromfile='a/tqftpserv.c', tofile='b/tqftpserv.c')))
own = repo / 'linux-port/radio/samurai-tftp-ram.c'
ro = repo / 'reference/kernel88/ro-firmware.c'
def command(args, label):
    p = subprocess.run(args, capture_output=True)
    (out / (label + '.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, (label, p.stderr.decode()[-1800:])
    return p
host_test = out / 'test-tftp-ram-host'
command(['gcc', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(here / 'test-tftp-ram.c'), str(own), str(ro), '-o', str(host_test)], 'host-test-build')
test = command([str(host_test), str(out)], 'host-test-run')
assert not test.stderr
arm_test = out / 'test-tftp-ram-arm64'
command(['aarch64-linux-gnu-gcc', '-O2', '-Wall', '-Wextra', '-Werror', '-static', str(here / 'test-tftp-ram.c'), str(own), str(ro), '-o', str(arm_test)], 'arm-test-build')
binary = out / 'samurai-tqftpserv-ram'
common = ['aarch64-linux-gnu-gcc', '-D_GNU_SOURCE', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-I' + str(base / 'qrtr/include'), '-I' + str(base / 'tqftpserv')]
links = [str(own), str(base / 'qrtr/lib/qrtr.c'), str(base / 'qrtr/lib/logging.c'), str(ro)]
command(common + [str(out / 'tqftpserv.c')] + links + ['-o', str(binary)], 'server-build')
isolated = source.replace('qrtr_publish(fd, 4096, 1, 0)', 'qrtr_publish(fd, 4096, 1, 206)')
assert isolated != source and isolated.replace('qrtr_publish(fd, 4096, 1, 206)', 'qrtr_publish(fd, 4096, 1, 0)') == source
(out / 'tqftpserv-isolated.c').write_text(isolated)
command(common + [str(out / 'tqftpserv-isolated.c')] + links + ['-o', str(out / 'samurai-tqftpserv-isolated')], 'isolated-server-build')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
r = dict(stage=206, source_work_file_sha256=sha(own), base_server_source_sha256=hashlib.sha256(before.encode()).hexdigest(), server_source_sha256=sha(out / 'tqftpserv.c'), candidate_sha256=sha(binary), candidate_bytes=binary.stat().st_size, native_fixture_asan_ubsan_passed=True, arm64_fixture_built=True, runtime_deployed=False, maximum_file_bytes=8388608, cache_must_be_private_tmpfs=True, readonly_firmware_translation_retained=True)
(here / 'tftp-build-validation.json').write_text(json.dumps(r, indent=2) + '\n')
print(json.dumps(r))
