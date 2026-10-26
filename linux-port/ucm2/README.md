# Samurai audio overlay

Install into a live or staged Alpine rootfs using `python3 linux-port/scripts/install-audio-ucm.py --root ROOTFS`. The target must provide Python 3, amixer and alsa-lib UCM support, plus the Samurai kernel jack and SLIM configuration from kernel172 or later. The installer changes only the two board UCM files and `/usr/libexec/samurai-audio-route`.

The HiFi verb chooses an initial playback/capture backend from the real CARD jack controls before PulseAudio opens its PCM. Device enables then select Speaker, Headphones, Mic or Headset. The helper preserves jack-owned DAPM pins, analog volume and Class-H mode, serializes route changes on the ALSA control node, and restores the previous route after an ALSA operation fails. Repeated selection does not restart the stream. Device disable leaves routing available until the verb closes; PCM close still powers down amplifiers.

Headphones use AIF1 PB, SLIM RX0/1 and RX INT1/2. The headset microphone uses the board's AMIC2/ADC2 via DEC1/TX1 on the existing mono AIF1 capture backend. JackHWMute describes the kernel-enforced inverse speaker/handset pins. PulseAudio currently exposes four device-pair profiles; real insertion, profile switching, headphones and headset sampling still require physical validation. Raw test recordings remain private. See [173 evidence](../../reference/kernel173/README.md).

On the current Phosh system, callaudiod owns port selection and deliberately unloads PulseAudio module-switch-on-port-available. Its absence after startup is expected; do not add a second routing policy solely because that module is missing. See [174 source and reboot evidence](../../reference/kernel174/README.md). Physical insertion and profile selection remain unverified.
