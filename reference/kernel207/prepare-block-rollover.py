"""Keep full source snapshots for an isolated old/new native comparison."""
from pathlib import Path
import difflib, hashlib, json, shutil, subprocess
here = Path(__file__).resolve().parent
repo = here.parents[1]
out = Path('/mnt/e/edk2-samurai-out/kernel207/block-rollover')
out.mkdir(mode=0o700)
old = out.parent.parent / 'kernel206/tftp-clean-rebuild-r2'
before = (old / 'tqftpserv/tqftpserv.c').read_text()
assert hashlib.sha256(before.encode()).hexdigest() == '20b9d630ffdf89d7fae4c19ce25710c87fd36dde3ac850eb9bc1eed6f45c04eb'
source = before.replace('\tuint16_t blk_expected;', '\tsize_t blk_expected;')
anchor = '\tclient->read_eof = send_len < client->blksize + 4;'
assert source.count(anchor) == 1
source = source.replace(anchor, anchor + '\n\tclient->block = block;')
start = source.index('\tlast = buf[2] << 8 | buf[3];', source.index('static int handle_reader('))
end = source.index('\n\treturn 1;\n}', start)
source = source[:start] + '''\tlast = buf[2] << 8 | buf[3];
\t/* Wire numbers wrap; file offsets and window progress must not. */
\tif (last != (uint16_t)client->block)
\t\treturn 1;
\tif (client->read_eof)
\t\treturn 0;

\tsize_t acknowledged = client->block;
\tfor (size_t i = 0; i < client->wsize; i++) {
\t\tsize_t absolute = acknowledged + i + 1;
\t\tsize_t offset = client->seek + (absolute - 1) * client->blksize;
\t\tn = tftp_send_data(client, absolute, offset, 0);
\t\tif (n < 0)
\t\t\treturn -1;
\t\tif (client->read_eof)
\t\t\tbreak;
\t}
''' + source[end:]
# Reader no longer uses a 16-bit loop variable.
start = source.index('static int handle_reader('); end = source.index('static int handle_writer(', start)
reader = source[start:end].replace('\tuint16_t block;\n', '')
source = source[:start] + reader + source[end:]
start = source.index('\t/* Check if we recieved expected block */', source.index('static int handle_writer('))
end = source.index('\n\tif (payload >', start)
source = source[:start] + '''\tif (block != (uint16_t)client->blk_expected) {
\t\t/* A repeated DATA block must never be appended a second time. */
\t\tif (block == (uint16_t)(client->blk_expected - 1)) {
\t\t\tif (client->block == client->blk_expected - 1)
\t\t\t\ttftp_send_ack(client->sock, block);
\t\t\treturn 1;
\t\t}
\t\ttftp_send_error(client->sock, TFTP_ERROR_EBADOP, "Block number out of sequence");
\t\treturn -1;
\t}
\tsize_t absolute = client->blk_expected++;
''' + source[end:]
source = source.replace('(block % client->wsize == 0)', '(absolute % client->wsize == 0)')
needle = '\t\tclient->blk_offset = 0;\n\t\ttftp_send_ack(client->sock, block);'
assert source.count(needle) == 1
source = source.replace(needle, '\t\tclient->blk_offset = 0;\n\t\tclient->block = absolute;\n\t\ttftp_send_ack(client->sock, block);')
(out / 'tqftpserv-before.c').write_text(before)
(out / 'tqftpserv.c').write_text(source)
(here / 'tqftpserv-block-rollover.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True), source.splitlines(True), fromfile='a/tqftpserv.c', tofile='b/tqftpserv.c')))
own = repo / 'linux-port/radio'
common = ['aarch64-linux-gnu-gcc', '-D_GNU_SOURCE', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-I' + str(old / 'qrtr/include'), '-I' + str(old / 'tqftpserv')]
links = [str(own / 'samurai-tftp-ram.c'), str(old / 'qrtr/lib/qrtr.c'), str(old / 'qrtr/lib/logging.c'), str(own / 'ro-firmware.c')]
artifacts = {}
for name, text in [('old-isolated', before.replace('qrtr_publish(fd, 4096, 1, 0)', 'qrtr_publish(fd, 4096, 1, 207)')), ('new-isolated', source.replace('qrtr_publish(fd, 4096, 1, 0)', 'qrtr_publish(fd, 4096, 1, 207)')), ('new-production', source)]:
    path = out / (name + '.c'); path.write_text(text)
    binary = out / name
    p = subprocess.run(common + [str(path)] + links + ['-o', str(binary)], capture_output=True)
    (out / (name + '-build.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0 and not p.stderr, (name, p.stderr.decode())
    artifacts[name] = hashlib.sha256(binary.read_bytes()).hexdigest()
(out / 'artifacts-private.json').write_text(json.dumps(artifacts, indent=2) + '\n')
print(json.dumps(dict(source_before=hashlib.sha256(before.encode()).hexdigest(), source_after=hashlib.sha256(source.encode()).hexdigest(), artifacts=artifacts, compiler_warnings=0, product_source_not_yet_modified=True)))
