"""Read the interrupt-thread path implicated by the sealed capture."""
from pathlib import Path
import re

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
queries = {
    'drivers/soc/qcom/smp2p.c': r'irq|notifier|callback|intr|spin_lock|ack|handshake',
    'drivers/remoteproc/qcom_q6v5.c': r'irq|handover|stop|spin_lock|qcom_scm',
    'drivers/remoteproc/qcom_q6v5_pas.c': r'handover|spin_lock|qcom_scm|qcom_pas_disable|clk_disable',
    'drivers/soc/qcom/smem.c': r'hwspin|spin_lock|qcom_smem_get|__qcom_smem_get',
    '.config': r'^CONFIG_(FUNCTION_TRACER|FUNCTION_GRAPH_TRACER|IRQSOFF_TRACER|PREEMPT_TRACER|KPROBES|KPROBE_EVENTS|FTRACE|TRACE_IRQFLAGS|SCHED_TRACER)='
}
for name, expression in queries.items():
    print(name)
    for number, line in enumerate(root.joinpath(name).read_text().splitlines(), 1):
        if re.search(expression, line):
            print(f'{number}: {line}')
