#!/bin/sh
set -eu

DEST='/home/cy122/orig-Ubuntu-20261119'
SRC='/mnt/orig-ro/home/cy122'

mkdir -p "$DEST"
echo "DEST=$DEST"

copy_item() {
    item=$1
    src="$SRC/$item"
    if [ ! -e "$src" ]; then
        echo "MISSING $src" >&2
        return 0
    fi
    if [ -e "$DEST/$item" ]; then
        echo "EXISTS $item" >&2
        return 0
    fi
    echo "COPY $item"
    tar -C "$SRC" -cpf - "$item" | tar -C "$DEST" -xpf -
}

copy_item samurai-dist-repo samurai-dist-repo
copy_item samurai-build samurai-build
copy_item samurai-stable-repo samurai-stable-repo
copy_item linux-samurai-github linux-samurai-github
copy_item standard-arm64-v7.3.1 standard-arm64-v7.3.1
copy_item pmaports-samurai-userspace pmaports-samurai-userspace
copy_item at2 at2
copy_item aptest aptest
copy_item samurai-install.log samurai-install.log
copy_item samurai-libcamera-build.log samurai-libcamera-build.log
copy_item samurai-v731.dts samurai-v731.dts
copy_item standard-arm64-v7.3.1.patch standard-arm64-v7.3.1.patch
copy_item standard-arm64-v7.3.1-camera.patch standard-arm64-v7.3.1-camera.patch
copy_item modules-v731-final.tar.gz modules-v731-final.tar.gz
copy_item modules-v731-camera.tar.gz modules-v731-camera.tar.gz
copy_item samurai-v731-modules.tar.zst samurai-v731-modules.tar.zst
copy_item samurai-bootstrap3.log samurai-bootstrap3.log
copy_item samurai-bootstrap4.log samurai-bootstrap4.log
copy_item samurai-bootstrap5.log samurai-bootstrap5.log
copy_item samurai-bootstrap6.log samurai-bootstrap6.log
copy_item .bash_history .bash_history
copy_item .bashrc .bashrc
copy_item .gitconfig .gitconfig
copy_item .git-credentials .git-credentials
copy_item .ssh .ssh
copy_item .gnupg .gnupg

echo "DONE"
find "$DEST" -mindepth 1 -maxdepth 1 -printf "%f\n" | sort
