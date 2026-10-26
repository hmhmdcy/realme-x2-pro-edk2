from pathlib import Path
from hashlib import sha256
import json, re, subprocess
k=Path('/home/cy122/x2pro-linux/linux')
files={'driver':'drivers/tty/serial/eud.c','printk':'kernel/printk/printk.c','printk_internal':'kernel/printk/internal.h','config':'.config','Image':'arch/arm64/boot/Image','DTB':'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'}
config=(k/'.config').read_text()
facts={'kernel_revision':subprocess.check_output(['git','-C',str(k),'rev-parse','HEAD'],text=True).strip(),
 'unchanged_core_diff':subprocess.check_output(['git','-C',str(k),'diff','--name-only','--','kernel/printk/printk.c','kernel/printk/internal.h'],text=True).strip(),
 'sha256':{name:sha256((k/path).read_bytes()).hexdigest() for name,path in files.items()},
 'init_sha256':sha256(Path('/home/cy122/x2pro-linux/initramfs/init').read_bytes()).hexdigest(),
 'selected_config':[s for s in config.splitlines() if re.match(r'(?:# )?CONFIG_(?:PREEMPT(?:_BUILD|_RT|_DYNAMIC|_LAZY|ION|_COUNT)?|SMP|NR_CPUS|HZ(?:_250)?|PRINTK(?:_TIME|_CALLER)?|RCU_CPU_STALL_TIMEOUT)(?:=| )',s)],
 'preempt_rt_enabled':'CONFIG_PREEMPT_RT=y' in config.splitlines(),
 'source_ranges':{'eud_console_write':'drivers/tty/serial/eud.c:417-435','eud_tx_work':'drivers/tty/serial/eud.c:253-291','eud_rx_irq':'drivers/tty/serial/eud.c:660-696','eud_rx_work_grace':'drivers/tty/serial/eud.c:765-795','console_emit_next_record':'kernel/printk/printk.c:3126-3195','devkmsg_write':'kernel/printk/printk.c:737-798','record_and_thread_limits':'kernel/printk/internal.h:30-51'},
 'claims':['Current legacy console holds UART lock over all bytes; RX IRQ increments counters only after acquiring it.',
           'Current non-RT printk core disables local IRQs around legacy con->write; force_legacy_kthread is false for this config.',
           'TTY worker unlocks between paced four-byte frames. PREEMPT=y excludes the earlier unverified nonpreempt-worker premise.',
           'The devkmsg single-write limit is 1024 bytes; the injected write was 1009 bytes.',
           'Driver-only per-frame unlocking would still leave printk outer IRQ disable; no such change was made.',
           'Host overlap is measured; physical arrival, actual IRQ entry delay and hardware acceptance are not measured.'],
 'primary_urls':['https://docs.kernel.org/core-api/printk-basics.html','https://docs.kernel.org/driver-api/tty/console.html','https://github.com/quic/eud']}
assert not facts['unchanged_core_diff']
Path('/mnt/e/edk2-samurai-out/rx51/source-audit.json').write_text(json.dumps(facts,indent=2)+'\n')
print(json.dumps({'kernel_revision':facts['kernel_revision'],'core_unchanged':True,'selected_config':facts['selected_config'],'driver_sha256':facts['sha256']['driver']}))
