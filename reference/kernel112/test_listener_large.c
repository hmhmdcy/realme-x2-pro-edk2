/* Exercise the actual listener path with a simulated method-4/5 transport. */
#include <assert.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "listener.c"

static unsigned char *wire;
static uint32_t wire_size;
static int mode, tail_calls;

int fastrpc2(const struct fastrpc_function_def_interp2 *def,
             int fd, uint32_t handle, ...)
{
    va_list ap;
    assert(fd == 7 && handle == ADSP_LISTENER_HANDLE);
    va_start(ap, handle);
    if (def->msg_id == 4) {
        (void)va_arg(ap, uint32_t);
        (void)va_arg(ap, uint32_t);
        (void)va_arg(ap, uint32_t);
        (void)va_arg(ap, void *);
        *va_arg(ap, uint32_t *) = 123;
        *va_arg(ap, uint32_t *) = 1;
        *va_arg(ap, uint32_t *) = REMOTE_SCALARS_MAKE(5, 2, 1);
        *va_arg(ap, uint32_t *) = mode == 3 ? 4U * 1024 * 1024 + 1 : wire_size;
        uint32_t cap = va_arg(ap, uint32_t);
        void *dst = va_arg(ap, void *);
        assert(cap == 256);
        memcpy(dst, wire, wire_size < cap ? wire_size : cap);
    } else {
        assert(def->msg_id == 5 && def->in_nums == 2 && def->in_bufs == 0);
        assert(def->out_nums == 1 && def->out_bufs == 1);
        assert(va_arg(ap, uint32_t) == 123);
        uint32_t offset = va_arg(ap, uint32_t);
        uint32_t *required = va_arg(ap, uint32_t *);
        uint32_t cap = va_arg(ap, uint32_t);
        void *dst = va_arg(ap, void *);
        assert(offset == 256 && cap == wire_size - offset);
        tail_calls++;
        if (mode == 1) {va_end(ap); return -5;}
        *required = mode == 2 ? wire_size + 1 : wire_size;
        memcpy(dst, wire + offset, cap);
    }
    va_end(ap);
    return 0;
}

static void check(uint32_t payload_size, int failure)
{
    unsigned char *payload = malloc(payload_size);
    for (uint32_t i = 0; i < payload_size; i++) payload[i] = (i * 17U + 3U) & 255;
    uint32_t nums[] = {5, payload_size};
    struct fastrpc_io_buffer input[] = {{.s=sizeof(nums), .p=nums}, {.s=payload_size, .p=payload}};
    wire_size = outbufs_calculate_size(2, input);
    wire = malloc(wire_size);
    outbufs_encode(2, input, wire);
    mode = failure; tail_calls = 0;
    uint32_t rctx = 0, handle = 0, sc = 0;
    struct fastrpc_io_buffer *decoded = NULL;
    int ret = return_for_next_invoke(7, 0, &rctx, &handle, &sc, NULL, &decoded);
    if (failure) {
        assert(ret != 0 && decoded == NULL);
        assert(tail_calls == (failure == 3 ? 0 : 1));
    } else {
        assert(ret == 0 && rctx == 123 && handle == 1);
        assert(decoded[0].s == sizeof(nums) && !memcmp(decoded[0].p, nums, sizeof(nums)));
        assert(decoded[1].s == payload_size && !memcmp(decoded[1].p, payload, payload_size));
        assert(tail_calls == (wire_size > 256 ? 1 : 0));
        iobuf_free(2, decoded);
    }
    free(wire); free(payload);
}

int main(void)
{
    check(16, 0); check(232, 0); check(233, 0); check(4096, 0);
    check(4096, 1); check(4096, 2); check(4096, 3);
    puts("PASS: actual listener preserves small/256-byte/large payloads; retrieval errors, mismatched lengths and oversize requests fail safely");
    return 0;
}
