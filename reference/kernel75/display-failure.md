# Session 75 physical display failure

The user reports stationary full-screen colored noise, without flicker. The
attached handset photograph confirms colored noise. Its SHA256 is
`eb174bce95e4f59ef1214838ef6488beb289ca734812c349cc8a84a3a3f9f4da`;
the photograph remains local.

On kernel build #72, boot ID `5093ea6a-ef56-4dc1-bd84-6296190bbc80`, the CPU
framebuffer has intact black-background/white-text fbcon output. It is 1080x2400,
XR24, 32 bpp with a 4352-byte stride. The decoded framebuffer image is local
`console.png`. No inference of a correct physical display is permitted from
that capture, successful KMS operations, vblank interrupts or DPU CRCs.

A bounded static-white native KMS test produced eight matching DPU CRC pairs
`25e11871 / 25e11871`. During its three-minute hold the user still saw colored
noise. The program then completed its panel-off/on and console restoration.
This establishes a physical display failure despite valid digital scanout
before the DSC/DSI output. GPU Vulkan render/readback tests are separate.

Current priorities are DSC encoding/routing, panel decompression setup, DSI
transport and inherited boot-display state. No hardware damage is established.
PPS payload matches the handset's own stock parameters byte for byte. Current
DSC registers and the stock source agree on 8-bpp Q4 encoding, slice 540x30,
picture 1080x2400, flatness threshold and endian-flip configuration; this does
not yet prove the emitted stream is correct. Measured DSI bit rate is about
370.6 Mbps/lane, while the stock mode explicitly requests 1.107 Gbps/lane.
The rate difference is a hypothesis to test, not a diagnosed cause.

A read-only diagnostic build records inherited SM8150 DSC register values
before Linux reprogramming, to compare with the native values. Neither the
static-white tool nor this diagnostic changes Android, userdata, GPT, EUD
transport settings or supply voltages.

## EOT-only candidate

Build #74, boot ID `a4543a18-48bb-488c-b3da-139a6957a004`, disabled EOT append. The initial capture had no DSI worker errors and the host EOT register was zero, yet the user still saw colored noise during a static-white hold. The whole logdump readback matched 1b457172fe3203e3c73833b5f7eb0d497cfebb215310bcf1f36b72e490a0a49a and the boot-image prefix matched 43ddcba2444e1672cd95205f6984c761eaeb59c83162cffdffb371c50a29c37b. This is a failed physical display candidate, not a fix.

The next candidate additionally restores stock noncontinuous clock mode. The controller code explicitly clears an inherited forced-HS request and the PHY forced-clock bits.

## Accepted noncontinuous-clock configuration

Build #75 cleared EOT append and the inherited controller/PHY forced-clock
requests. After its first panel power cycle, the user confirmed the white hold
as "已经全白，没有噪点". Its early log still contained 147 DSI worker messages;
those ended at 104.57 s. This is not evidence of a clean first boot.

The final #76 removes only the read-only DSC register diagnostics. On a fresh
boot, before any display recovery cycle, the user confirmed native color bars
as "彩条清晰，显示正常". Complete logs contain zero DSI worker errors, no
unhandled SMMU context fault or kernel Oops, and taint remains zero. Its 9,036
real A640 draws and nine panel power cycles pass. These optical observations
support the deployed configuration; EOT-only was insufficient. We did not
change the measured link rate, supply voltages, DSC PPS or EUD transport.

The same final #76 image was rebooted again without a flash. Boot ID
`af922f36-bacd-481d-a5c5-21c8e3fada65` passes twelve additional GPU draws and
three panel power cycles, with zero DSI worker errors in the complete log.
Total verified GPU draws are 39,096; final-build regression panel cycles are
twelve. The second boot adds automated evidence, not a second optical report.
