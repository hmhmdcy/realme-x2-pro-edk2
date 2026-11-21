# samurai-apps

Meta package for the complete Plasma Mobile application set used by the
Samurai rootfs.  It is intentionally separate from `samurai-desktop`: the
board layer stays thin, while this package can be installed or removed as a
unit.

The set follows the postmarketOS `_pmb_recommends` list plus the applications
that aarch64 Plasma Mobile does not select automatically:

- `firefox-esr` and `mobile-config-firefox`;
- `discover` with the native apk backend and the fwupd backend;
- the Plasma Mobile recommendations and web extras;
- common desktop tools (`konsole`, `kate`, `ark`, `gwenview`, `kcalc`,
  `spectacle`).

`plasma-camera` is deliberately excluded.  Alpine builds it against
libcamera 0.8, while the board camera stack pins
`libcamera=99990.7.2-r33` with the 0.7 ABI.  Installing the current Alpine
binary would break `samurai-camera-config` and `samurai-camera-stack`.
