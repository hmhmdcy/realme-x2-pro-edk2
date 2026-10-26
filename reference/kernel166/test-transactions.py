from pathlib import Path
import json, runpy, re

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel166')
shared=runpy.run_path(str(ref/'run-tests.py'))
k=shared['k'];out=shared['out'];function=shared['function'];run=shared['run'];ngd=shared['ngd']
prior=ref.parent/'kernel139'
header=(prior/'fault-injection-stubs.h').read_text()
header=header.replace('struct dma_chan { int unused; };',
'''struct dma_device { void *device_prep_slave_sg, *device_prep_config_sg; };
struct dma_chan { struct dma_device *device; };
#define dev_err_once(...) ((void)0)
static int pm_error;
static struct dma_chan test_tx, test_rx;
''')
header=header.replace('struct device *dev; void *tx_base; uintptr_t tx_phys_base;',
'''struct device *dev; void *tx_base; uintptr_t tx_phys_base;
 struct dma_chan *dma_rx_channel; int state; struct { void *handle; } qmi;''')
header=header.replace('static int pm_runtime_get_sync(struct device *d) { ++get_count; return ++d->pm_votes; }',
'''static int pm_runtime_get_sync(struct device *d) {
 ++get_count; ++d->pm_votes; return pm_error ? pm_error : d->pm_votes;
}
static void pm_runtime_put_noidle(struct device *d) { ++put_count; --d->pm_votes; }
''')
macros=[]
for source in [(k/'include/linux/slimbus.h').read_text(),(k/'drivers/slimbus/slimbus.h').read_text(),ngd]:
    lines=source.splitlines(True);i=0
    while i<len(lines):
        if re.match(r'#define\s+(?:SLIM_\w+|QCOM_SLIM_NGD_DESC_NUM)\b',lines[i]):
            macro=lines[i]
            while lines[i].rstrip().endswith('\\'):
                i+=1;macro+=lines[i]
            macros.append(macro)
        i+=1
header+='\n'+''.join(macros)
slimheader=(k/'drivers/slimbus/slimbus.h').read_text()
# These two inline predicates contain no mocks or state transitions.
for name in ['slim_tid_txn','slim_ec_txn']:
    header+=function(slimheader,name)
names=['qcom_slim_ngd_tx_msg_get','qcom_slim_ngd_tx_msg_dma_cb','qcom_slim_ngd_tx_msg_post','qcom_slim_ngd_xfer_msg']
extracted=''.join(function(ngd,n) for n in names)+function((k/'drivers/slimbus/messaging.c').read_text(),'slim_do_transfer')
main=(prior/'fault-injection-main.c').read_text()
main=main.replace('ngd.dev = &dev; ngd.tx_base = buffer;',
                  'ngd.dev = &dev; ngd.tx_base = buffer; ngd.dma_tx_channel=&test_tx; ngd.dma_rx_channel=&test_rx; pm_error=0;')
main=main.replace('bool ok[12]','bool ok[14]')
main=main.replace(' int passed = 0;', '''
 reset(SLIM_MSG_MC_REQUEST_VALUE); pm_error=-EREMOTEIO;
 ret=slim_do_transfer(&core,&txn);
 ok[12]=ret==-EREMOTEIO && !dev.pm_votes && !active_ids() && !prep_count && slots_clear();
 reset(SLIM_MSG_MC_REQUEST_VALUE); ngd.dma_tx_channel=NULL;
 ret=slim_do_transfer(&core,&txn);
 ok[13]=ret==-EHOSTDOWN && !dev.pm_votes && !active_ids() && !prep_count && slots_clear();
 int passed = 0;''')
main=main.replace('i < 12','i < 14').replace('passed == 12','passed == 14')
result=json.loads(run('transactions-candidate',header+extracted+main))
report=json.loads((ref/'host-tests-validation.json').read_text())
report['transactions']=result
for folder in [ref,out]:
    (folder/'host-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(result))
