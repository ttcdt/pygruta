#!/bin/sh

MOD_PREFIX=""
BIN_PREFIX="/usr/local/bin"

for p in /usr/local/lib/python3*/*-packages ; do
    if [ -d $p ] ; then
        MOD_PREFIX="$p"
    fi
done

# parse arguments
while [ $# -gt 0 ] ; do

    case $1 in
    --help)              CONFIG_HELP=1 ;;
    --bin-prefix)        BIN_PREFIX=$2 ; shift ;;
    --bin-prefix=*)      BIN_PREFIX=`echo $1 | sed -e 's/--prefix=//'` ;;
    --mod-prefix)        MOD_PREFIX=$2 ; shift ;;
    --mod-prefix=*)      MOD_PREFIX=`echo $1 | sed -e 's/--prefix=//'` ;;
    esac

    shift
done

if [ "$CONFIG_HELP" = "1" ] ; then

    echo "Available options:"
    echo "--bin-prefix=PREFIX       Installation path for binary ($BIN_PREFIX)."
    echo "--mod-prefix=PREFIX       Installation path for python3 module ($MOD_PREFIX)."

    exit 1
fi

echo "Configuring..."

PYTHON_PATH=$(which python3)

if [ "$PYTHON_PATH" = "" ] ; then
    echo "Cannot find python3 path. Is it installed?"
    exit 2
fi

if [ "$MOD_PREFIX" = "" ] ; then
    echo "Cannot find a path for local Python3 packages."
    echo "Set if with --mod-prefix."
    exit 2
fi

rm -f makefile.opts
echo "BIN_PREFIX=$BIN_PREFIX" >> makefile.opts
echo "MOD_PREFIX=$MOD_PREFIX" >> makefile.opts
echo "PYTHON_PATH=$PYTHON_PATH" >> makefile.opts

cat makefile.opts makefile.in > Makefile

echo "Run 'make install' to install."

exit 0
