from pathlib import Path
import re

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel180')
path = root / 'drivers/soc/qcom/pdr_interface.c'
source = path.read_text()
backup = out / 'pdr_interface.c.attempt1-private'
if backup.exists():
    assert backup.read_text() == source
else:
    backup.write_text(source)
for name in ('changed-w1-build-private.log', 'full-build-private.log', 'Image-k180-pdr-irq-private'):
    existing = out / name
    dest = out / ('attempt1-' + name)
    if existing.is_file():
        assert not dest.exists()
        existing.rename(dest)
    else:
        assert dest.is_file()
source = source.replace('\tu64 locator_attempt;\n', '\tu64 locator_attempt;\n\tstruct qmi_txn *register_txn;\n', 1)
marker = 'static int pdr_locator_new_server('
assert source.count(marker) == 1
helper = '''/* list_lock keeps the stack transaction alive until its owner detaches it. */
static void pdr_cancel_registration(struct pdr_handle *pdr, struct pdr_service *pds)
{
\tstruct qmi_txn *txn = pds->register_txn;

\tlockdep_assert_held(&pdr->list_lock);
\tif (!txn)
\t\treturn;
\tmutex_lock(&txn->lock);
\ttxn->result = -ENETRESET;
\tcomplete(&txn->completion);
\tmutex_unlock(&txn->lock);
\tpds->register_txn = NULL;
}

'''
source = source.replace(marker, helper + marker, 1)
source = source.replace('static int pdr_register_listener(struct pdr_handle *pdr, const char *service_path,\n\t\t\t\t struct sockaddr_qrtr *addr, bool enable, int *state)',
                        'static int pdr_register_listener(struct pdr_handle *pdr, struct pdr_service *pds,\n\t\t\t\t struct sockaddr_qrtr *addr, u64 generation,\n\t\t\t\t bool enable, int *state)', 1)
source = source.replace('\tstruct servreg_register_listener_resp resp = { };',
                        '\tconst char *service_path = pds->service_path;\n\tstruct servreg_register_listener_resp resp = { };', 1)
marker = '\treq.enable = enable;'
source = source.replace(marker, '''\tmutex_lock(&pdr->list_lock);
\tif (pdr->stopping || pds->lookup_failed || !pds->service_connected ||
\t    pds->server_generation != generation) {
\t\tmutex_unlock(&pdr->list_lock);
\t\tqmi_txn_cancel(&txn);
\t\treturn -ENETRESET;
\t}
\tpds->register_txn = &txn;
\tmutex_unlock(&pdr->list_lock);

''' + marker, 1)
marker = '''\tif (ret < 0) {
\t\tqmi_txn_cancel(&txn);
\t\treturn ret;
\t}

\tret = qmi_txn_wait(&txn, 5 * HZ);
\tif (ret < 0) {
'''
first = source.index('static int pdr_register_listener(')
last = source.index('/* status_lock orders callbacks;', first)
listener = source[first:last]
assert listener.count(marker) == 1
listener = listener.replace(marker, '''\tif (ret < 0) {
\t\tmutex_lock(&pdr->list_lock);
\t\tif (pds->register_txn == &txn)
\t\t\tpds->register_txn = NULL;
\t\tmutex_unlock(&pdr->list_lock);
\t\tqmi_txn_cancel(&txn);
\t\treturn ret;
\t}

\tret = qmi_txn_wait(&txn, 5 * HZ);
\tmutex_lock(&pdr->list_lock);
\tif (pds->register_txn == &txn)
\t\tpds->register_txn = NULL;
\tmutex_unlock(&pdr->list_lock);
\t/* Server loss/release explicitly completed the transaction, not a timeout. */
\tif (ret == -ENETRESET)
\t\treturn ret;
\tif (ret < 0) {
''', 1)
source = source[:first] + listener + source[last:]
source = source.replace('pdr_register_listener(pdr, pds->service_path, &addr, true, &state)',
                        'pdr_register_listener(pdr, pds, &addr, generation, true, &state)', 1)
source = source.replace('\t\tpds->server_generation++;\n', '\t\tpdr_cancel_registration(pdr, pds);\n\t\tpds->server_generation++;\n', 1)
source = source.replace('\t\t\tpds->server_generation++;\n', '\t\t\tpdr_cancel_registration(pdr, pds);\n\t\t\tpds->server_generation++;\n', 1)
source = source.replace('\tpds->lookup_failed = true;', '\tpdr_cancel_registration(pdr, pds);\n\tpds->lookup_failed = true;', 1)
# Pair the allocation error path with locator callbacks before cancel_work_sync.
source = source.replace('release_qmi_handle:\n\tWRITE_ONCE(pdr->stopping, true);\n\tcancel_work_sync',
                        'release_qmi_handle:\n\tWRITE_ONCE(pdr->stopping, true);\n\tmutex_lock(&pdr->lock);\n\tpdr->locator_init_complete = false;\n\tmutex_unlock(&pdr->lock);\n\tcancel_work_sync', 1)
marker = '\tWRITE_ONCE(pdr->stopping, true);\n\tmutex_unlock(&pdr->list_lock);'
assert source.count(marker) == 1
source = source.replace(marker, '''\tWRITE_ONCE(pdr->stopping, true);
\tlist_for_each_entry(pds, &pdr->lookups, node)
\t\tpdr_cancel_registration(pdr, pds);
\tlist_for_each_entry(pds, &pdr->retired, node)
\t\tpdr_cancel_registration(pdr, pds);
\tmutex_unlock(&pdr->list_lock);''', 1)
path.write_text(source)
print('K180_CANCEL_AND_ERROR_RELEASE_REFINED')
