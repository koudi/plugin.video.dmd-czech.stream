# -*- coding: utf-8 -*-

import stream
import sys

container_url = sys.argv[1]
show_url = sys.argv[2]
subscribe = sys.argv[3]

stream.favourite(show_url, subscribe=='true')

xbmc.executebuiltin("Container.Update(%s, replace)" % container_url)

