#!/bin/bash

mkdir tempbuild
cp -R pokemonReference/. tempbuild/.
cd tempbuild
pip install -t . -r requirements.txt
zip -r ../build-$(date "+%Y%m%d.%H_%M_%S").zip *
cd ..
rm -r tempbuild
