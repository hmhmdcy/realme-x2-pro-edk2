from pathlib import Path
import difflib, shutil
O=Path('/mnt/e/edk2-samurai-out/kernel91')
R=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel91')
up=O.parent/'kernel90/rmtfs'
dst=O/'rmtfs-cow-src'
assert not dst.exists()
shutil.copytree(up,dst)
before=(up/'rmtfs.c').read_text()
s=before.replace('unsigned int txn;','unsigned int txn = 0;').replace('unsigned txn;','unsigned txn = 0;')
s=s.replace('struct rmtfs_iovec_entry *entries;', 'struct rmtfs_iovec_entry *entries = NULL;')
s=s.replace('dbgprintf("[RMTFS] close %s', 'dbgprintf("[RMTFS] close %u')
s=s.replace('sector_base = entries[i].sector_addr * SECTOR_SIZE;', 'sector_base = (off_t)entries[i].sector_addr * SECTOR_SIZE;')
s=s.replace('if (rmtfd) {\n\t\tqmi_result_error(&resp.result', 'if (!rmtfd) {\n\t\tqmi_result_error(&resp.result')
needle='\tfor (i = 0; i < num_entries; i++) {\n\t\tphys_base = entries[i].phys_offset;'
assert s.count(needle)==1
s=s.replace(needle, '''\tif (is_write > 1 || num_entries > 255) {
\t\tqmi_result_error(&resp.result, QMI_RMTFS_ERR_MALFORMED_MSG);
\t\tgoto respond;
\t}
\tunsigned total_sectors = 0;
\tfor (i = 0; i < num_entries; i++) {
\t\tif (entries[i].num_sector > 32768 ||
\t\t    entries[i].sector_addr > 32768 - entries[i].num_sector ||
\t\t    total_sectors > 32768 - entries[i].num_sector) {
\t\t\tqmi_result_error(&resp.result, QMI_RMTFS_ERR_MALFORMED_MSG);
\t\t\tgoto respond;
\t\t}
\t\ttotal_sectors += entries[i].num_sector;
\t}
'''+needle)
# Replace CLI and remoteproc automation. The coordinator starts/stops MPSS explicitly.
s=s.replace('static int sig_int_count;\n\nstatic int run_rmtfs', 'static int run_rmtfs')
start=s.index('int main(int argc, char **argv)')
s=s[:start]+'''int main(int argc, char **argv)
{
\tstruct sigaction action = {};
\tint ret;
\tif (argc != 1) {
\t\tfprintf(stderr, "No options accepted: RAM COW and fixed snapshots only\\n");
\t\treturn 1;
\t}
\t(void)argv;
\tsetvbuf(stdout, NULL, _IOLBF, 0);
\tdbgprintf_enabled = true;
\tsigemptyset(&action.sa_mask);
\taction.sa_handler = sig_int_handler;
\tsigaction(SIGINT, &action, NULL);
\tsigaction(SIGTERM, &action, NULL);
\trmem = rmtfs_mem_open();
\tif (!rmem) return 1;
\tret = storage_init("/tmp/k91-nv", true, false);
\tif (ret) { rmtfs_mem_close(rmem); return 1; }
\tputs("RMTFS RAM COW ready; no persistent storage writes");
\tdo { ret = run_rmtfs(-1); } while (ret == -ENETRESET && !sig_int_count);
\tstorage_exit();
\trmtfs_mem_close(rmem);
\treturn ret < 0 ? 1 : 0;
}
'''
(dst/'rmtfs.c').write_text(s)
(R/'rmtfs-cow-handler.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/rmtfs.c',tofile='b/rmtfs.c')))
shutil.copyfile(R/'storage-cow.c',dst/'storage.c')
shutil.copyfile(R/'sharedmem-bounded.c',dst/'sharedmem.c')
# These symbols remain in upstream's event loop, but fail closed and cannot
# open or write remoteproc sysfs. No rproc.c or libudev is linked.
(dst/'rproc-disabled.c').write_text('''#include <errno.h>
int rproc_start(void) { return -EPERM; }
int rproc_stop(void) { return -EPERM; }
''')
print('Prepared fixed-input RAM-COW service, no rproc automation or memory fallback')
