#!/usr/bin/env python3

import sys
from libnmap.parser import NmapParser, NmapParserException


report = NmapParser.parse_fromfile(sys.argv[1])

for host in report.hosts:
    for s in host.services:
        if s.service == "ssh":
            print(str(host.address)+":"+str(s.port)+" > "+str(s.service))
