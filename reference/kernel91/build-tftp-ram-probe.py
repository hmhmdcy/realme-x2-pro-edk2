from pathlib import Path
import hashlib,subprocess,difflib
O=Path('/mnt/e/edk2-samurai-out/kernel91'); B=O.parent/'kernel88'
R=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel91')
before=(B/'tqftpserv/tqftpserv.c.before').read_text()
s=before.replace('int main(int argc, char **argv)\n{','int main(int argc, char **argv)\n{\n\tsetvbuf(stdout, NULL, _IOLBF, 0);')
s=s.replace('client = calloc(1, sizeof(*client));\n\tclient->sq', 'client = calloc(1, sizeof(*client));\n\tif (!client) goto out_close_sock;\n\tclient->sq')
# The WRQ destination is only server_check.txt. Reject oversized negotiation,
# maintain a 4096-byte write limit, and use the correct ACK for optionless WRQ.
start=s.index('static void handle_wrq('); end=s.index('static int handle_reader(',start)
wrq=s[start:end]
wrq=wrq.replace('\tfd = translate_open(filename, O_WRONLY | O_CREAT);','''\tlog_debug("WRQ options: block=%zu window=%zu size=%zd seek=%lld\\n", blksize, wsize, tsize, (long long)seek);
\tif (blksize > 65535 || wsize > 128 || blksize * wsize > 1048576 || seek != 0 || tsize > 4096) {
\t\ttftp_send_error_to(sq, TFTP_ERROR_EACCESS, "RAM probe limits");
\t\treturn;
\t}
\tfd = translate_open(filename, O_WRONLY | O_CREAT);''')
wrq=wrq.replace('tftp_send_data(client, 1, 0, 0);','tftp_send_ack(client->sock, 0);')
s=s[:start]+wrq+s[end:]
s=s.replace('char buf[128];','char buf[129];').replace('recvfrom(client->sock, buf, sizeof(buf), 0,','recvfrom(client->sock, buf, sizeof(buf)-1, MSG_TRUNC,')
s=s.replace('recvfrom(client->sock, buf, client->blksize + 4, 0,','recvfrom(client->sock, buf, client->blksize + 4, MSG_TRUNC,')
needle='\t/* Drop unsolicited messages */'
first=s.index(needle,s.index('static int handle_reader('))
s=s[:first]+'\tif (len < 4 || len > 128) return -1;\n\n'+s[first:]
second=s.index(needle,s.index('static int handle_writer('))
s=s[:second]+'\tif (len < 4 || (size_t)len > client->blksize + 4) return -1;\n\n'+s[second:]
s=s.replace('\t/* Copy the data to the destination buffer */','''\tif (payload > client->rw_buf_size - client->blk_offset) return -1;
\t/* Copy the data to the destination buffer */''')
s=s.replace('\t\tret = write(client->fd, client->rw_buf, client->blk_offset);','''\t\toff_t pos = lseek(client->fd, 0, SEEK_CUR);
\t\tif (pos < 0 || pos > 4096 || client->blk_offset > 4096 - (size_t)pos) {
\t\t\ttftp_send_error(client->sock, TFTP_ERROR_ENOSPACE, "RAM probe limit");
\t\t\treturn -1;
\t\t}
\t\tret = write(client->fd, client->rw_buf, client->blk_offset);''')
s=s.replace('if (ret < 0) {\n\t\t\tlog_err("failed to write data:', 'if (ret < 0 || (size_t)ret != client->blk_offset) {\n\t\t\tlog_err("failed to write data:')
(O/'tqftpserv-ram-probe.c').write_text(s)
(R/'tftp-ram-probe.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/tqftpserv.c',tofile='b/tqftpserv.c')))
subprocess.run(['aarch64-linux-gnu-gcc','-D_GNU_SOURCE','-O2','-static','-I'+str(B/'qrtr/include'),'-I'+str(B/'tqftpserv'),str(O/'tqftpserv-ram-probe.c'),str(R/'tftp-ram-probe.c'),str(B/'qrtr/lib/qrtr.c'),str(B/'qrtr/lib/logging.c'),str(R.parent/'kernel88/ro-firmware.c'),'-o',str(O/'tqftpserv-ram-probe')],check=True)
print(hashlib.sha256((O/'tqftpserv-ram-probe').read_bytes()).hexdigest())
