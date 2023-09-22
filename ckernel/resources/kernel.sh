#! /usr/bin/env -S bash -l

export CKERNEL_NAME="{name}"
export CKERNEL_INSTALL_DIR="{installdir}"

if [ -e "{script}" ]; then
    source "{script}"
fi

python3 -m ckernel run -f "${{1}}"
