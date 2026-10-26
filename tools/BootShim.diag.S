_Head:
        /* Set _Entry address */
        adr     x1, _Payload

        /* Jump to the real code */
        b       _Start

        /* Fake Linux kernel header */

_StackBase0: //has to be 0 on some devices
        /* Text Offset */
        .quad 0

_StackSize0:
        /* Image Size */
        .quad 0

        /* Flags */
        .quad 0

        /* Reserved */
        .quad 0

        /* Reserved */
        .quad 0

        /* Reserved */
        .quad 0

        /* ARM64 Magic */
        .ascii "ARM\x64"

        /* Reserved */
        .long 0

        .ascii "EDK2-MSM"

_StackBase:
        /* Text Offset */
        .quad UEFI_BASE

_StackSize:
        /* Image Size */
        .quad UEFI_SIZE

_Start:
        /* DIAG-1: paint live XBL framebuffer GREEN 0xFF00FF00 (0x9D000000, 1080x2400x32bpp) */
        movz    x7, #0x9D00, lsl #16
        movz    w8, #0xFF00, lsl #16
        movk    w8, #0xFF00
        movz    x11, #0x27, lsl #16
        movk    x11, #0x8D00
_DiagGreen:
        str     w8, [x7], #4
        subs    x11, x11, #1
        b.ne    _DiagGreen

        mov     x4, x1
        ldr     x5, _StackBase
        cmp     x4, x5
        beq     _Entry
        ldr     x6,     _StackSize

_CopyLoop:
        ldp     x2, x3, [x4], #16
        stp     x2, x3, [x5], #16
        subs    x6, x6, #16
        b.ne    _CopyLoop

        /* DIAG-2: UEFI payload copied -> paint framebuffer RED 0xFFFF0000 */
        movz    x7, #0x9D00, lsl #16
        movz    w8, #0xFFFF, lsl #16
        movz    x11, #0x27, lsl #16
        movk    x11, #0x8D00
_DiagRed:
        str     w8, [x7], #4
        subs    x11, x11, #1
        b.ne    _DiagRed

        ldr     x5, _StackBase

_Entry:
        br      x5

_Dead:
        /* We should never get here */
        b       _Dead

.text
.align 4

_Payload:
        /* Your code will get ran right after this binary */
