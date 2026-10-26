"""Complete bounded large-input retrieval using the public FastRPC method 5.

Protocol reference: Android external/fastrpc, android-12.1.0_r20,
src/adsp_listener_stub.c and src/listener_android.c.
"""
from pathlib import Path

src = Path('/home/cy122/hexagonrpc-v04-k112/hexagonrpcd')
pending = {}
def edit(name, old, new):
    p = src / name
    text = pending.get(p, p.read_text())
    assert text.count(old) == 1, name
    pending[p] = text.replace(old, new)

edit('interfaces/adsp_listener.def',
     'HEXAGONRPC_DEFINE_REMOTE_METHOD(4, adsp_listener_next2, 2, 1, 4, 1)',
     'HEXAGONRPC_DEFINE_REMOTE_METHOD(4, adsp_listener_next2, 2, 1, 4, 1)\n'
     'HEXAGONRPC_DEFINE_REMOTE_METHOD(5, adsp_listener_get_in_bufs2, 2, 0, 1, 1)')
edit('listener.c', '#include <stdio.h>', '#include <stdio.h>\n#include <string.h>')
edit('listener.c', '\tchar inbufs[256];',
     '\tchar inbufs[256];\n\tchar *large_inbufs = NULL;\n\tconst char *input = inbufs;')
edit('listener.c', '''\tif (inbufs_len > 256) {
\t\tfprintf(stderr, "Large (>256B) input buffers aren't implemented\\n");
\t\tret = -1;
\t\tgoto err_free_outbufs;
\t}''', '''\tif (inbufs_len > sizeof(inbufs)) {
\t\tuint32_t required = 0;
\t\t/* Bound allocations before accepting a DSP-supplied length. */
\t\tif (inbufs_len > 4U * 1024 * 1024) {
\t\t\tfprintf(stderr, "Large input exceeds 4 MiB bound\\n");
\t\t\tret = -1;
\t\t\tgoto err_free_outbufs;
\t\t}
\t\tlarge_inbufs = malloc(inbufs_len);
\t\tif (!large_inbufs) {
\t\t\tret = -1;
\t\t\tgoto err_free_outbufs;
\t\t}
\t\tmemcpy(large_inbufs, inbufs, sizeof(inbufs));
\t\tret = fastrpc2(&adsp_listener_get_in_bufs2_def, fd,
\t\t\t\tADSP_LISTENER_HANDLE, *rctx, (uint32_t)sizeof(inbufs),
\t\t\t\t&required, inbufs_len - (uint32_t)sizeof(inbufs),
\t\t\t\tlarge_inbufs + sizeof(inbufs));
\t\tif (ret || required != inbufs_len) {
\t\t\tfprintf(stderr, "Large input retrieval failed: ret=%d required=%u expected=%u\\n",
\t\t\t\tret, required, inbufs_len);
\t\t\tret = -1;
\t\t\tgoto err_free_outbufs;
\t\t}
\t\tinput = large_inbufs;
\t\tprintf("large-input(%u) completed\\n", inbufs_len);
\t}''')
edit('listener.c', 'ret = inbuf_decode(ctx, inbufs_len, inbufs);',
     'ret = inbuf_decode(ctx, inbufs_len, input);')
edit('listener.c', 'err_free_outbufs:\n\tfree(outbufs);',
     'err_free_outbufs:\n\tfree(large_inbufs);\n\tfree(outbufs);')
for path, text in pending.items():
    path.write_text(text)
print('Bounded method-5 large-input retrieval patch applied')
