"""Reuse only the old boundary stubs, not its main or 21-case test program."""
from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
old=HERE.parent/'usb-input-native-pm-link-candidate/test-native-pm.c'
raw=old.read_bytes();assert hashlib.sha256(raw).hexdigest()=='3c5f1e3de5286ea20f281fcf7136e57482306bb43585df53e060b7327fbfcb42'
text=raw.decode().split('int main(void)')[0]
text=text.replace('static void *system_wq=', '''#define IRQF_ONESHOT 0x2000UL
#define IRQ_HANDLED 1
typedef int irqreturn_t;
static int irq_requests,irq_failed_at,irqs_released;
static irqreturn_t samurai_usb_event(int irq,void *data);
static int platform_get_irq_byname_optional(struct platform_device *p,const char *name)
{ assert(p);return !strcmp(name,"usbin-plugin")?7:9; }
static void release_irq(void *data)
{ int irq=(int)(intptr_t)data;assert(allocated->paused&&!published);
  unsigned int before=queued;assert(samurai_usb_event(irq,allocated)==IRQ_HANDLED);assert(before==(unsigned int)queued);
  irqs_released++;event(irq==7?'i':'j'); }
static int devm_request_threaded_irq(struct device *d,int irq,void *primary,
 irqreturn_t (*thread)(int,void *),unsigned long flags,const char *name,void *data)
{ assert(d&&!primary&&flags==IRQF_ONESHOT&&thread==samurai_usb_event&&data==allocated);
  assert(allocated->paused&&!published&&link_refs>0&&allocated->native_consumer);
  assert(!strcmp(name,irq==7?"usbin-plugin":"usbin-src-change"));irq_requests++;
  unsigned int before=queued;assert(thread(irq,data)==IRQ_HANDLED);assert(before==(unsigned int)queued);
  if(irq_requests==irq_failed_at)return -EIO;
  actions[action_count].fn=release_irq;actions[action_count++].data=(void *)(intptr_t)irq;
  event(irq==7?'A':'B');return 0; }
static int dev_err_probe(struct device *dev,int error,const char *msg)
{ assert(dev&&!strcmp(msg,"USB input events\\n"));return error; }
static void *system_wq=''')
# Stubs above need their existing state declarations, so place them immediately
# before the actual merged functions, not before the original variables.
begin=text.index('#define IRQF_ONESHOT');end=text.index('static void *system_wq=',begin)
added=text[begin:end];text=text[:begin]+text[end:]
anchor='#include "actual-link-and-probe.inc"'
assert anchor in text
text=text.replace(anchor,added+'\n#include "actual-link-irq-probe.inc"')
text=text.replace('action_count==1&&allocated->native_consumer','action_count==3&&allocated->native_consumer')
text=text.replace('require_link=native_retained=false;', 'irq_requests=irq_failed_at=irqs_released=0;require_link=native_retained=false;')
text += (HERE/'test-main.c.inc').read_text()
(HERE/'test-merge.c').write_text(text,encoding='utf-8',newline='\n')
print(hashlib.sha256((HERE/'test-merge.c').read_bytes()).hexdigest())
