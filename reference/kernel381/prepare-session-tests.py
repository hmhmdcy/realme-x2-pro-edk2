from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel379/check-session.py').read_text().replace('stage=379','stage=381').replace('+[44]', '+[44,45]')
assert '+[44,45]' in s
(HERE/'check-session.py').write_text(s)
s=(HERE.parent/'kernel379/session-regression.c').read_text()
anchor='#include "body.inc"';assert s.count(anchor)==1
s=s.replace(anchor,'static unsigned ipe_resets;static int ipe_reset_error;\nstatic int camss_a5_ipe_quiesce(struct camss_a5_resources *r){(void)r;ipe_resets++;return ipe_reset_error?-ETIMEDOUT:0;}\n'+anchor)
anchor=' if(scenario>=30){';assert s.count(anchor)==1
s=s.replace(anchor,''' if(scenario==45){
  a.ipe_dma_pending=true;a.request_fw_mapped=true;ipe_reset_error=1;
  assert(model_stop(&a)==-ETIMEDOUT && a.ipe_dma_pending && a.request_fw_mapped && !a.cpu_enabled && !a.irq_enabled && a.power_held && backing && !pm_calls && !free_calls && ipe_resets==1 && pc_commands==1);
  ipe_reset_error=0;assert(!model_stop(&a) && !a.ipe_dma_pending && !a.request_fw_mapped && !a.power_held && !backing && ipe_resets==2 && pc_commands==1);return 0;
 }
'''+anchor)
(HERE/'session-regression.c').write_text(s)
print('Prepared actual parser/session/stop regression including failed IPE reset retention and retry.')
