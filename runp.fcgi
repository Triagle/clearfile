#!/usr/bin/env python
from clearfile import clearfile
from flipflop import WSGIServer

WSGIServer(clearfile.app).run()
