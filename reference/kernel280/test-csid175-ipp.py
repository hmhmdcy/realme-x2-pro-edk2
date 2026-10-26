"""Run actual gen2 CSID code against OEM-pinned register oracles and mock MMIO."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel280')
source = (TREE / 'drivers/media/platform/qcom/camss/camss-csid-gen2.c').read_text()
header = (TREE / 'drivers/media/platform/qcom/camss/camss-csid-gen2.h').read_text()
pin = json.loads((ROOT / 'oem-version-sources.json').read_text())
row = next(value for key,value in pin['sources'].items() if key.endswith('/cam_ife_csid175.h'))
oem = (PRIVATE / row['local_name']).read_bytes()
assert hashlib.sha256(oem).hexdigest() == row['sha256']


def oem_field(name):
    return int(re.search(r'\.' + name + r'\s*=\s*(0x[0-9a-fA-F]+|\d+)', oem.decode())[1], 0)


mapping = {'CSID_IPP_IRQ_STATUS': 'csid_pxl_irq_status_addr',
           'CSID_IPP_IRQ_MASK': 'csid_pxl_irq_mask_addr',
           'CSID_IPP_IRQ_CLEAR': 'csid_pxl_irq_clear_addr',
           'CSID_IPP_CFG0': 'csid_pxl_cfg0_addr', 'CSID_IPP_CFG1': 'csid_pxl_cfg1_addr',
           'CSID_IPP_CTRL': 'csid_pxl_ctrl_addr', 'CSID_IPP_STATUS': 'csid_pxl_status_addr',
           'CSID_IPP_FRM_DROP_PERIOD': 'csid_pxl_frm_drop_period_addr',
           'CSID_IPP_FRM_DROP_PATTERN': 'csid_pxl_frm_drop_pattern_addr',
           'CSID_IPP_IRQ_SUBSAMPLE_PERIOD': 'csid_pxl_irq_subsample_period_addr',
           'CSID_IPP_IRQ_SUBSAMPLE_PATTERN': 'csid_pxl_irq_subsample_pattern_addr',
           'CSID_IPP_PIX_DROP_PERIOD': 'csid_pxl_pix_drop_period_addr',
           'CSID_IPP_PIX_DROP_PATTERN': 'csid_pxl_pix_drop_pattern_addr',
           'CSID_IPP_LINE_DROP_PERIOD': 'csid_pxl_line_drop_period_addr',
           'CSID_IPP_LINE_DROP_PATTERN': 'csid_pxl_line_drop_pattern_addr'}
for macro, field in mapping.items():
    actual = int(re.search(r'#define\s+' + macro + r'\s+(0x[0-9a-fA-F]+)', source)[1], 0)
    assert actual == oem_field(field), (macro, field)
assert oem_field('pix_store_en_shift_val') == 7
assert [oem_field(x) for x in ['dt_id_shift_val', 'vc_shift_val', 'dt_shift_val', 'fmt_shift_val', 'path_en_shift_val']] == [27,22,16,12,31]


def function(signature):
    start = source.index(signature)
    return source[start:source.index('\n}\n', start) + 3]


defines = source[source.index('#define CSID_RST_STROBES'):source.index('static void __csid_configure_rx')]
defines += '\n'.join(line for line in header.splitlines() if line.startswith('#define ') and not line.endswith('_H'))
functions = ''.join(function(signature) for signature in [
    'static void __csid_configure_rx(', 'static void __csid_ctrl_rdi(',
    'static void __csid_configure_testgen(', 'static void __csid_configure_rdi_stream(',
    'static bool csid_gen2_port_is_ipp(', 'static int csid_gen2_validate_ipp(',
    'static int csid_gen2_configure_ipp(', 'static int csid_gen2_stop_ipp(',
    'static int csid_configure_stream(', 'static irqreturn_t csid_isr('])
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef int irqreturn_t;
#define BIT(n) (1u << (n))
#define IRQ_HANDLED 1
#define MSM_CSID_PAD_FIRST_SRC 1
#define MSM_CSID_MAX_SRC_STREAMS 4
#define CSID_RESET_TIMEOUT_MS 500
struct v4l2_mbus_framefmt { u32 width, height, code; };
struct csid_format_info { u32 code; u8 data_type, decode_format, bpp, spp; };
struct csid_formats { unsigned int nformats; const struct csid_format_info *formats; };
struct csid_subdev_resources { bool is_lite, has_ipp; const struct csid_formats *formats; };
struct csid_phy_config { bool is_cphy; u8 csiphy_id, lane_cnt; u32 lane_assign, en_vc; };
struct csid_testgen_config { bool enabled; unsigned int mode; };
struct camss { void *dev; };
struct csid_device {
    unsigned char *base;
    const struct csid_subdev_resources *res;
    struct csid_phy_config phy;
    struct csid_testgen_config testgen;
    struct v4l2_mbus_framefmt fmt[5];
    struct camss *camss;
    unsigned int id;
    int reset_complete;
};
static bool csid_is_lite(const struct csid_device *csid) { return csid->res->is_lite; }
static const struct csid_format_info *csid_get_fmt_entry(const struct csid_format_info *formats,
                                                        unsigned int count, u32 code)
{
    for (unsigned int i=0; i<count; i++) if (formats[i].code==code) return &formats[i];
    return formats;
}
static unsigned char *mmio;
static struct { u32 address, value; } writes[1024];
static u32 reads[1024];
static unsigned int nwrites, nreads, fifo_errors;
static int ready_after;
static u32 mmio_read(const void *address)
{
    size_t offset=(const unsigned char *)address-mmio;
    assert(offset<4096 && !(offset&3) && nreads<1024);
    reads[nreads++]=offset;
    if (offset==0x254 && ready_after>0 && --ready_after==0) *(u32 *)(mmio+offset)=1;
    return *(const u32 *)(mmio+offset);
}
static void mmio_write(u32 value, void *address)
{
    size_t offset=(unsigned char *)address-mmio;
    assert(offset<4096 && !(offset&3) && nwrites<1024);
    writes[nwrites].address=offset; writes[nwrites++].value=value;
    *(u32 *)(mmio+offset)=value;
}
#define readl mmio_read
#define readl_relaxed mmio_read
#define writel mmio_write
#define writel_relaxed mmio_write
#define dev_err_ratelimited(dev, ...) do { (void)(dev); fifo_errors++; } while(0)
#define complete(value) (++*(value))
#define readl_poll_timeout(address, value, condition, delay, timeout) \
    ({ int result=-ETIMEDOUT; (void)(delay); (void)(timeout); \
       for (unsigned int attempt=0;attempt<4;attempt++) { \
           value=readl(address); if (condition) { result=0; break; } } result; })
'''
tests = r'''
static struct csid_format_info formats[] = {
    { 10, 0x2b, 2, 10, 1 }, { 12, 0x2c, 3, 12, 1 }, { 8, 0x2a, 1, 8, 1 },
    { 16, 0x2e, 5, 16, 1 }, { 20, 0x1e, 1, 8, 2 }, { 30, 0x2b, 15, 10, 1 },
};
static void clear_trace(void) { nwrites=nreads=0; }
static unsigned int write_count(u32 address)
{
    unsigned int n=0; for(unsigned int i=0;i<nwrites;i++) n+=writes[i].address==address;
    return n;
}
static u32 reg(u32 address) { return *(u32 *)(mmio+address); }
int main(void)
{
    mmio=calloc(1,4096); assert(mmio);
    struct csid_formats info={ .nformats=sizeof(formats)/sizeof(formats[0]), .formats=formats };
    struct csid_subdev_resources resource={ .has_ipp=true, .formats=&info };
    struct camss camss={0};
    struct csid_device csid={ .base=mmio, .res=&resource, .camss=&camss };
    csid.phy.lane_cnt=3; csid.phy.lane_assign=0x210; csid.phy.is_cphy=true;
    for(unsigned int i=0;i<5;i++) csid.fmt[i]=(struct v4l2_mbus_framefmt){ .width=640, .height=480, .code=10 };
    csid.phy.en_vc=BIT(3);
    assert(csid_configure_stream(&csid,1)==0);
    assert(reg(0x200)==0x802b2083u); /* OEM175: real RAW10 decode, PIX_STORE, CID0. */
    assert((reg(0x200)>>27&3)==0);
    assert(reg(0x204)==2 && reg(0x208)==1 && reg(0x34)==4);
    const u32 periods[]={0x210,0x218,0x228,0x230};
    const u32 patterns[]={0x20c,0x214,0x224,0x22c};
    for(unsigned int i=0;i<4;i++) assert(reg(periods[i])==1 && reg(patterns[i])==0);
    assert(write_count(0x600)==0); /* Full IPP is not RDI3 / TPG. */
    assert(reg(0x100)==(2u | 0x210u<<4 | 1u<<24)); /* C-PHY receiver. */

    for(unsigned int i=0;i<info.nformats;i++) {
        clear_trace(); csid.fmt[4].code=formats[i].code;
        int result=csid_gen2_configure_ipp(&csid,3,31);
        if (i>=4) { assert(result==-EINVAL && nwrites==0); continue; }
        assert(result==0);
        u32 golden=0x80000083u | (u32)formats[i].decode_format<<12 |
                   (u32)formats[i].data_type<<16 | 31u<<22;
        assert(reg(0x200)==golden);
    }
    clear_trace(); csid.fmt[4].code=999;
    assert(csid_gen2_configure_ipp(&csid,3,0)==-EINVAL && nwrites==0);
    csid.fmt[4].code=10;
    assert(csid_gen2_configure_ipp(&csid,3,32)==-EINVAL && nwrites==0);
    assert(csid_gen2_configure_ipp(&csid,0,0)==-EINVAL && nwrites==0);
    csid.fmt[4].code=20; csid.phy.en_vc=BIT(0)|BIT(3);
    assert(csid_configure_stream(&csid,1)==-EINVAL && nwrites==0);

    csid.fmt[4].code=10; csid.phy.en_vc=BIT(3);
    assert(csid_configure_stream(&csid,1)==0);
    clear_trace(); ready_after=3; *(u32 *)(mmio+0x254)=0;
    assert(csid_configure_stream(&csid,0)==0);
    assert(!(reg(0x200)&BIT(31)) && reg(0x208)==0 && reg(0x34)==0);
    assert(writes[nwrites-1].address==0x200); /* Disable after halt acknowledgement. */
    clear_trace(); assert(csid_gen2_stop_ipp(&csid)==0 && nwrites==0);

    assert(csid_configure_stream(&csid,1)==0);
    *(u32 *)(mmio+0x254)=0; ready_after=0; clear_trace();
    assert(csid_configure_stream(&csid,0)==-ETIMEDOUT);
    assert(reg(0x200)&BIT(31)); /* A timeout must not pretend the path is disabled. */
    assert(write_count(0x200)==0);

    clear_trace(); csid.phy.en_vc=BIT(0);
    assert(csid_configure_stream(&csid,1)==0);
    assert(reg(0x300)==0x802bf007u && write_count(0x200)==0);
    resource.is_lite=true; resource.has_ipp=false; csid.phy.en_vc=BIT(3); clear_trace();
    assert(csid_configure_stream(&csid,1)==0);
    assert(reg(0x500)==0x982bf007u && write_count(0x200)==0);
    assert(!csid_gen2_port_is_ipp(&csid,3));

    resource.is_lite=false; resource.has_ipp=true; csid.phy.en_vc=BIT(3);
    csid.testgen.enabled=true; csid.testgen.mode=9; clear_trace();
    assert(csid_configure_stream(&csid,1)==0);
    assert(reg(0x610)==(480u | 640u<<16));
    assert(reg(0x614)==0x2b && reg(0x200)==0x802b2083u);
    assert(writes[nwrites-1].address==0x600 && (writes[nwrites-1].value&1));
    *(u32 *)(mmio+0x254)=0; ready_after=3; clear_trace();
    assert(csid_configure_stream(&csid,0)==0 && !(reg(0x600)&1));
    assert(writes[nwrites-1].address==0x600 && write_count(0x600)==1);
    unsigned int disabled_at=0;
    for(unsigned int i=0;i<nwrites;i++) if(writes[i].address==0x200) disabled_at=i;
    assert(disabled_at<nwrites-1); /* The pixel path halted before the TPG stopped. */
    assert(csid_configure_stream(&csid,1)==0);
    *(u32 *)(mmio+0x254)=0; ready_after=0; clear_trace();
    assert(csid_configure_stream(&csid,0)==-ETIMEDOUT);
    assert(write_count(0x600)==0 && (reg(0x600)&1)); /* No false successful source stop. */
    csid.testgen.enabled=false;
    *(u32 *)(mmio+0x30)=4; *(u32 *)(mmio+0x70)=1; clear_trace();
    assert(csid_isr(0,&csid)==IRQ_HANDLED && fifo_errors==1 && csid.reset_complete==1);
    assert(reg(0x38)==4);
    unsigned int top_reads=0; for(unsigned int i=0;i<nreads;i++) top_reads+=reads[i]==0x70;
    assert(top_reads==1); /* IPP status uses 0x30, not the nonexistent fourth RDI. */
    free(mmio);
    puts("actual CSID gen2 IPP/RDI/TPG/IRQ and halt failure tests passed");
    return 0;
}
'''
test_source = PRIVATE / 'csid175-ipp-host.c'
test_binary = PRIVATE / 'csid175-ipp-host'
test_source.write_text(prefix + defines + '\n' + functions + tests)
subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                '-Wno-unused-parameter', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                str(test_source), '-o', str(test_binary)], check=True)
run = subprocess.run([str(test_binary)], capture_output=True, text=True)
(PRIVATE / 'csid175-ipp-host-private.log').write_text(run.stdout + run.stderr)
report = dict(stage=280, exit=run.returncode, diagnostics=run.stderr,
              source_sha256=hashlib.sha256(test_source.read_bytes()).hexdigest(),
              production_functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),
              oem175_register_fields_checked=len(mapping), actual_production_functions=True,
              tests=['RAW8/10/12/16 actual decode and CID0', 'VC31 and invalid VC32',
                     'reject unknown/YUV/payload-only formats before any MMIO',
                     'all drop/subsample periods and patterns', 'C-PHY receiver',
                     'acknowledged halt before disable', 'halt timeout propagated and enable retained',
                     'idempotent inactive stop', 'RDI0 preserved', 'lite RDI3 not IPP',
                     'TPG starts after arming and stops after halt acknowledgement',
                     'TPG remains untouched on halt failure', 'IPP IRQ/FIFO/reset acknowledgement'],
              only_simulated_mmio=True, no_handset_ipp_writes=True)
(ROOT / 'csid175-host-tests-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
print(run.stdout)
assert run.returncode == 0 and not run.stderr
