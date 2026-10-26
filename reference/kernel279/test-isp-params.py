"""Exercise actual core/parser and backend validation with exact-sized buffers.

The callback body is extracted from the candidate, never reimplemented here.
ASan catches reads beyond a legitimate header-only DISABLE block.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel279')
name = sys.argv[1]
assert name in ('before-fix', 'after-fix')
if name == 'before-fix':
    assert not (ROOT / 'params-before-fix-validation.json').exists(), 'Retain the original negative control'


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start) + 3]


core = (TREE / 'drivers/media/v4l2-core/v4l2-isp.c').read_text()
backend = (TREE / 'drivers/media/platform/qcom/camss/camss-vfe-780.c').read_text()
callback = function(backend, 'static int vfe_params_aec_bhist_validate(')
implementation = function(core, 'int v4l2_isp_params_validate_buffer_size(')
implementation += function(core, 'int v4l2_isp_params_validate_buffer(')
implementation += callback
mmio = ''
if name == 'after-fix':
    pp = (TREE / 'drivers/media/platform/qcom/camss/camss-vfe-880-pp.c').read_text()
    for register in ['IFE_STATS_AEC_BHIST_MODULE_CFG', 'IFE_STATS_AEC_BHIST_RGN_OFFSET_CFG',
                     'IFE_STATS_AEC_BHIST_RGN_NUM_CFG']:
        mmio += next(line for line in pp.splitlines() if line.startswith('#define ' + register + ' ')) + '\n'
    mmio += r'''
typedef uint32_t u32;
#define BIT(n) (1u << (n))
#define min_t(type, a, b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
#define MSM_VFE_PAD_SINK 0
struct vfe_device { unsigned char *base; };
struct vfe_line { struct { u32 width, height; } fmt[1]; };
static u32 readl_relaxed(const void *address) { return *(const u32 *)address; }
static void writel_relaxed(u32 value, void *address) { *(u32 *)address = value; }
'''
    mmio += function(pp, 'void vfe_880_enable_aec_bhist(')
    mmio += function(pp, 'void vfe_880_set_aec_bhist_region(')
    mmio += function(backend, 'static void vfe_params_aec_bhist(')
    mmio += function(backend, 'static void vfe_params_apply(')
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <linux/qcom-camss-config.h>
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
struct device { int unused; };
struct vb2_buffer { size_t payload; };
#define vb2_get_plane_payload(vb, plane) ((vb)->payload)
#define dev_dbg(dev, ...) ((void)(dev))
struct v4l2_isp_params_block_type_info {
    size_t size;
    int (*block_validate)(struct device *, const struct v4l2_isp_block_header *);
};
'''
tests = r'''
static struct device device;
static const struct v4l2_isp_params_block_type_info info[] = {
    [CAMSS_PARAMS_AEC_BHIST] = {
        .size = sizeof(struct camss_params_aec_bhist),
        .block_validate = vfe_params_aec_bhist_validate,
    },
};
static int validate(struct v4l2_isp_buffer *buffer, size_t bytes)
{
    struct vb2_buffer vb = { .payload = bytes };
    int ret = v4l2_isp_params_validate_buffer_size(&device, &vb, 8192);
    if (ret) return ret;
    return v4l2_isp_params_validate_buffer(&device, &vb, buffer, info,
                                         sizeof(info) / sizeof(info[0]));
}
int main(void)
{
    size_t bytes = sizeof(struct v4l2_isp_buffer) + sizeof(struct v4l2_isp_block_header);
    struct v4l2_isp_buffer *buffer = calloc(1, bytes);
    assert(buffer);
    buffer->version = V4L2_ISP_VERSION_V1;
    buffer->data_size = sizeof(struct v4l2_isp_block_header);
    struct v4l2_isp_block_header *block = (void *)buffer->data;
    block->type = CAMSS_PARAMS_AEC_BHIST;
    block->size = sizeof(*block);
    block->flags = V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;
    assert(validate(buffer, bytes) == 0);
    MMIO_DISABLE_CASE
    block->flags = V4L2_ISP_PARAMS_FL_BLOCK_ENABLE | V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;
    assert(validate(buffer, bytes) == -EINVAL);
    block->flags = 0;
    assert(validate(buffer, bytes) == -EINVAL);
    block->flags = V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;
    block->size = 0;
    assert(validate(buffer, bytes) == -EINVAL);
    free(buffer);

    bytes = sizeof(struct v4l2_isp_buffer) + sizeof(struct camss_params_aec_bhist);
    buffer = calloc(1, bytes);
    assert(buffer);
    buffer->version = V4L2_ISP_VERSION_V1;
    buffer->data_size = sizeof(struct camss_params_aec_bhist);
    struct camss_params_aec_bhist *bhist = (void *)buffer->data;
    bhist->header.type = CAMSS_PARAMS_AEC_BHIST;
    bhist->header.size = sizeof(*bhist);
    bhist->width = 640;
    bhist->height = 480;
    assert(validate(buffer, bytes) == 0);
    bhist->header.flags = V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;
    assert(validate(buffer, bytes) == 0);
    MMIO_ENABLE_CASE
    bhist->header.flags = 0x8000;
    assert(validate(buffer, bytes) == -EINVAL);
    bhist->header.flags = 0;
    bhist->left = 1;
    assert(validate(buffer, bytes) == -EINVAL);
    bhist->left = 0;
    bhist->width = 0;
    assert(validate(buffer, bytes) == -EINVAL);
    bhist->width = 640;
    bhist->header.type = 255;
    assert(validate(buffer, bytes) == -EINVAL);
    bhist->header.type = CAMSS_PARAMS_AEC_BHIST;
    buffer->data_size++;
    assert(validate(buffer, bytes) == -EINVAL);
    buffer->data_size--;
    buffer->version = 2;
    assert(validate(buffer, bytes) == -EINVAL);
    free(buffer);
    puts("actual V4L2 ISP core/backend parameter boundary tests passed");
    return 0;
}
'''
if name == 'after-fix':
    tests = tests.replace('MMIO_DISABLE_CASE', r'''
    u32 *registers = calloc(1, 0x10000);
    assert(registers);
    struct vfe_device vfe = { .base = (unsigned char *)registers };
    struct vfe_line line = { .fmt = { { .width = 640, .height = 480 } } };
    registers[IFE_STATS_AEC_BHIST_MODULE_CFG / 4] = 0xaa01;
    vfe_params_apply(&vfe, &line, buffer);
    assert(registers[IFE_STATS_AEC_BHIST_MODULE_CFG / 4] == 0xaa00);
    ''').replace('MMIO_ENABLE_CASE', r'''
    vfe_params_apply(&vfe, &line, buffer);
    assert(registers[IFE_STATS_AEC_BHIST_MODULE_CFG / 4] == 0xaa01);
    assert(registers[IFE_STATS_AEC_BHIST_RGN_OFFSET_CFG / 4] == 0);
    assert(registers[IFE_STATS_AEC_BHIST_RGN_NUM_CFG / 4] == ((239u << 16) | 319));
    bhist->header.flags = 0;
    bhist->left = 638;
    bhist->top = 478;
    vfe_params_apply(&vfe, &line, buffer);
    assert(registers[IFE_STATS_AEC_BHIST_RGN_OFFSET_CFG / 4] == ((239u << 16) | 319));
    assert(registers[IFE_STATS_AEC_BHIST_RGN_NUM_CFG / 4] == 0);
    assert(registers[IFE_STATS_AEC_BHIST_MODULE_CFG / 4] == 0xaa01);
    bhist->header.flags = V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;
    vfe_params_apply(&vfe, &line, buffer);
    assert(registers[IFE_STATS_AEC_BHIST_MODULE_CFG / 4] == 0xaa00);
    bhist->header.flags = 0;
    vfe_params_apply(&vfe, &line, buffer);
    assert(registers[IFE_STATS_AEC_BHIST_MODULE_CFG / 4] == 0xaa00);
    bhist->left = bhist->top = 0;
    free(registers);
    ''')
else:
    tests = tests.replace('MMIO_DISABLE_CASE', '').replace('MMIO_ENABLE_CASE', '')
source = PRIVATE / ('params-' + name + '.c')
binary = PRIVATE / ('params-' + name)
source.write_text(prefix + implementation + mmio + tests)
subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                '-D__EXPORTED_HEADERS__',
                '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                '-I' + str(TREE / 'include/uapi'), str(source), '-o', str(binary)], check=True)
run = subprocess.run([str(binary)], capture_output=True, text=True)
(PRIVATE / ('params-' + name + '-private.log')).write_text(run.stdout + run.stderr)
report = dict(stage=279, case=name, exit=run.returncode,
              source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              backend_callback_sha256=hashlib.sha256(callback.encode()).hexdigest(),
              heap_buffer_overflow='heap-buffer-overflow' in run.stderr,
              actual_mmio_helpers_and_flag_application=name == 'after-fix',
              actual_production_core_and_callback=True, phone_unchanged=True)
(ROOT / ('params-' + name + '-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
print((run.stdout + run.stderr)[:1600])
if name == 'before-fix':
    assert run.returncode != 0 and report['heap_buffer_overflow']
else:
    assert run.returncode == 0 and not run.stderr
