#!/usr/bin/python
# -*- coding: utf-8 -*-
# qrclock - The Quite Rubbish Clock for Raspberry Pi - scruss, 2013-01-19

import time
# need to use git://github.com/mozillazg/python-qrcode.git
import qrcode
from PIL import Image
import ImageOps
# uses bgreat's SPI code; see
# raspberrypi.org/phpBB3/viewtopic.php?f=32&t=9814&p=262274&hilit=nokia#p261925
import nokiaSPI

noki = nokiaSPI.NokiaSPI(brightness=64)              # create display device
#noki = nokiaSPI.NokiaSPI(dev=(0,0),contrast=0xc0,speed=500000,brightness=1023)
noki.cls()
noki.text("Why don't we do it in the road? Why dont' we do it in the road? Why don't we do it in the road?",wrap=True)
