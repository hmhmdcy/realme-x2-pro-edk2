# RX49 source audit: timeout bytes and usbmon scope

The [official libusb synchronous I/O documentation](https://libusb.sourceforge.io/api-1.0/group__libusb__syncio.html)
requires considering the transferred count even on timeout. Some bytes
may have moved before the timeout; a negative result alone is insufficient
to infer that no input arrived.

The [PyUSB libusb1 backend](https://github.com/pyusb/pyusb/blob/master/usb/backend/libusb1.py)
is only the public reference; the installed source was also read directly.
WSL has PyUSB 1.2.1-2 at
`/usr/lib/python3/dist-packages/usb/backend/libusb1.py`, SHA256
0c86fc30235ce1d762ae14721e19a5efcadd8eea7d94771d4767d9b099ffba60.
Its read method returns nonzero transferred bytes on LIBUSB_ERROR_TIMEOUT,
and raises for a zero-byte timeout. `installed-pyusb-read.txt` records the
actual method inspected, rather than assuming GitHub master is installed.
No backend/library change was made.

The [official usbmon documentation](https://docs.kernel.org/usb/usbmon.html)
and the local kernel's `Documentation/usb/usbmon.rst` describe callback
length as actual bytes. Payload exists only with the data tag `=`, and
captured data can be shorter than the reported actual length. The analyzer
therefore checks the captured length for each nonempty target bulk-IN
completion and refuses a full-stream equality claim if any data are absent
or truncated. Nonzero status with actual data is preserved and reported.

The current B trace has one canceled completion with actual=6. Its complete
wire bytes `90 04 67 69 63 3d` occur in raw, and both streams retain the
entire `gic=80 err=0` output. This supplies runtime evidence for handling
partial timeout/cancel data; the old seven traces had no such nonempty
error completion. Their complete IN streams also equal raw, including
RX43's stty sample with zero IN bytes at the measured boundary.
The observed -2 is a kernel URB status, not a recorded libusb return code;
the latter was not instrumented, so no specific native return code is claimed.

This usbmon observes the WSL vhci virtual host-controller URBs, downstream
of Windows USB/IP forwarding. It cannot measure physical ACK/data-toggle
or distinguish EUD TX from Windows upstream loss. It also bypasses the
installed qcusbser serial path. The immutable TX journal adds CPU-issued
MMIO evidence, without making physical device-delivery claims.

The first diagnostic helper omitted the installed terminal's display-side
ESC[6n suppression. This triggered local terminal response/echo, without
extra measured EUD RX input. The revised helper handles queries split
across frames and retains all raw/text bytes. Data frames still have one
attempt, LEN2 is avoided, and both reader/monitor workers close before
Windows reclaim. No device setup command, reset or data retry was added.
