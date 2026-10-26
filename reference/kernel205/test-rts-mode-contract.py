"""Exercise actual GENI/core C functions against a modeled register bank.

This is source-level API evidence, not a handset or UART timing test.
"""
from pathlib import Path
import hashlib,json,re,subprocess

here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel205/rts-contract');out.mkdir(mode=0o700)
driver=(k/'drivers/tty/serial/qcom_geni_serial.c').read_text();core=(k/'drivers/tty/serial/serial_core.c').read_text()
def function(source,name):
 start=source.index(name+'(');start=source.rfind('\n',0,start)+1
 # uart_update_mctrl's return type is on the preceding line.
 if source[start:start+len(name)]==name:start=source.rfind('\n',0,start-1)+1
 brace=source.index('{',start);level=1;end=brace+1
 while level:
  if source[end]=='{':level+=1
  elif source[end]=='}':level-=1
  end+=1
 return source[start:end]+'\n'
set_mctrl=function(driver,'qcom_geni_serial_set_mctrl');termios=function(driver,'qcom_geni_serial_set_termios');update=function(core,'uart_update_mctrl')
assert 'SE_UART_MANUAL_RFR' not in termios and 'set_mctrl(' not in termios
defs={};lines=driver.splitlines();i=0
while i<len(lines):
 line=lines[i]
 if line.startswith('#define '):
  body=line
  while body.rstrip().endswith('\\'):i+=1;body+='\n'+lines[i]
  name=re.match(r'#define\s+(\w+)',body)[1];defs[name]=body
 i+=1
needed=set(re.findall(r'\b[A-Z][A-Z0-9_]+\b',set_mctrl+termios));selected={}
while True:
 new={name:body for name,body in defs.items() if name in needed and name not in selected}
 if not new:break
 selected.update(new);needed.update(re.findall(r'\b[A-Z][A-Z0-9_]+\b','\n'.join(new.values())))
prefix=r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <sys/ioctl.h>
typedef uint32_t u32;
#define BIT(n) (1U << (n))
#define GENMASK(h,l) ((~0U << (l)) & (~0U >> (31-(h))))
#define SER_RS485_ENABLED 1U
#define WRITE_ONCE(x,v) ((x)=(v))
#define trace_geni_serial_set_mctrl(...) ((void)0)
#define trace_geni_serial_set_termios(...) ((void)0)
#define guard(name) fake_guard
struct uart_port;
struct uart_ops { void (*set_mctrl)(struct uart_port *,unsigned int); };
struct uart_port { unsigned int mctrl; struct { unsigned int flags; } rs485; bool suspended; unsigned char *membase; const struct uart_ops *ops; };
struct ktermios { unsigned int c_cflag; };
struct fake_se { int ignored; };
struct fake_data { int (*set_rate)(struct fake_se *,unsigned int); };
struct qcom_geni_serial_port { struct uart_port uport; bool manual_flow; unsigned int loopback; struct fake_se se; const struct fake_data *dev_data; unsigned int tx_fifo_depth; unsigned long poll_timeout_us; };
static void fake_guard(struct uart_port *p) { (void)p; }
static struct qcom_geni_serial_port *to_dev_port(struct uart_port *p) { return (struct qcom_geni_serial_port *)p; }
static bool uart_console(struct uart_port *p) { (void)p; return false; }
static void writel(u32 v,void *p) { memcpy(p,&v,sizeof(v)); }
static u32 readl(const void *p) { u32 v; memcpy(&v,p,sizeof(v)); return v; }
static unsigned int uart_get_baud_rate(struct uart_port *p,struct ktermios *t,const struct ktermios *o,unsigned int lo,unsigned int hi) { (void)p;(void)t;(void)o;(void)lo;(void)hi;return 115200; }
static unsigned int tty_get_char_size(unsigned int f) { (void)f;return 8; }
static void uart_update_timeout(struct uart_port *p,unsigned int f,unsigned int b) { (void)p;(void)f;(void)b; }
static unsigned long uart_fifo_timeout(struct uart_port *p) { (void)p;return 20; }
static unsigned long jiffies_to_usecs(unsigned long j) { return j*1000; }
static int set_rate(struct fake_se *p,unsigned int b) { (void)p;(void)b;return 0; }
'''
main=r'''
int main(void) {
 unsigned int mismatch=0,cases=0;
 const struct uart_ops ops={qcom_geni_serial_set_mctrl};
 const struct fake_data data={set_rate};
 for (unsigned int before=0;before<2;before++)
 for (unsigned int after=0;after<2;after++)
 for (unsigned int rts=0;rts<2;rts++)
 for (unsigned int suspended=0;suspended<2;suspended++) {
  u32 regs[1024]={0};
  struct qcom_geni_serial_port p={0};
  p.manual_flow=before;p.uport.mctrl=TIOCM_DTR|(rts?TIOCM_RTS:0);
  p.uport.ops=&ops;p.uport.membase=(unsigned char *)regs;p.uport.suspended=suspended;
  p.dev_data=&data;p.tx_fifo_depth=16;
  qcom_geni_serial_set_mctrl(&p.uport,p.uport.mctrl);
  struct ktermios t={.c_cflag=CS8|(after?0:CRTSCTS)};
  qcom_geni_serial_set_termios(&p.uport,&t,&t);
  /* Same requested RTS value: the actual core skips the callback. */
  uart_update_mctrl(&p.uport,rts?TIOCM_RTS:0,rts?0:TIOCM_RTS);
  u32 actual=readl(p.uport.membase+SE_UART_MANUAL_RFR);
  u32 expected=(after&&!rts&&!suspended)?UART_MANUAL_RFR_EN|UART_RFR_NOT_READY:0;
  if(actual!=expected)mismatch++;
  cases++;
 }
 printf("{\"cases\":%u,\"contract_mismatches\":%u}\n",cases,mismatch);
 return 0;
}
'''
anchor='\ttrace_geni_serial_set_termios(uport->dev,';assert termios.count(anchor)==1
sync='\tqcom_geni_serial_set_mctrl(uport, uport->mctrl);\n\n'
variants={'current':termios,'proposed_sync_at_end':termios.replace(anchor,sync+anchor),'wrong_sync_before_mode_update':termios.replace('\tif (termios->c_cflag & CRTSCTS) {',sync+'\tif (termios->c_cflag & CRTSCTS) {')}
results={}
for name,body in variants.items():
 path=out/(name+'.c');path.write_text(prefix+'\n'.join(selected.values())+'\n'+set_mctrl+'\n'+update+'\n'+body+'\n'+main)
 binary=out/name;p=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(path),'-o',str(binary)],capture_output=True);(out/(name+'-build-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr.decode())
 p=subprocess.run([str(binary)],capture_output=True,check=True);(out/(name+'-run-private.log')).write_bytes(p.stdout+p.stderr);assert not p.stderr;results[name]=json.loads(p.stdout)
assert results['current']==dict(cases=16,contract_mismatches=2)
assert results['proposed_sync_at_end']==dict(cases=16,contract_mismatches=0)
assert results['wrong_sync_before_mode_update']==dict(cases=16,contract_mismatches=2)
r=dict(stage=205,actual_driver_and_serial_core_functions_extracted=True,source_geni_sha256=hashlib.sha256(driver.encode()).hexdigest(),source_core_sha256=hashlib.sha256(core.encode()).hexdigest(),results=results,asan_ubsan_passed=True,register_bank_and_locking_modeled=True,hardware_and_concurrency_not_verified=True,not_proof_of_historical_phase5_cause=True,geni_product_source_not_modified=True)
(here/'rts-mode-contract-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
