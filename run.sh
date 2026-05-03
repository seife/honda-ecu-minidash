#!/bin/bash
# add the location where the phew code lives to MICROPYPATH
# the default MICROPYPATH is ".frozen:$HOME/.micropython/lib:/usr/lib/micropython",
# so you could also just install phew in $HOME/.micropython/lib instead...
MICROPYPATH=.frozen:/usr/lib/micropython:../phew micropython -m main
