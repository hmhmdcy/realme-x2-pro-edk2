#!/bin/sh
# Build samsinkinject.so inside an Alpine aarch64 container.
#
#   podman run --rm --arch arm64 \
#     -v "$PWD/linux-port/camera/preview-fastpath:/src:Z" -w /src \
#     alpine:edge sh /src/build.sh
set -e

apk add --no-cache gcc musl-dev pkgconf gstreamer-dev

gcc -shared -fPIC -O2 -Wall -Wextra \
  -o samsinkinject.so samsinkinject.c \
  $(pkg-config --cflags --libs gstreamer-1.0 gobject-2.0)

ls -l samsinkinject.so
