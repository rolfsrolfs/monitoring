#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Script that monitors operational status by fetching information from status pages
#
# usage:
#   python status-url.py https://status.teamviewer.com
# 
# This script works for:
#   https://status.inspera.no
#   https://status.dfo.no
#   https://status.teamviewer.com
#   https://status.zoom.us

import re
import requests
from bs4 import BeautifulSoup
import sys

if (len(sys.argv) < 2) or ( len(sys.argv) >= 2 and '-h' in sys.argv):
    sys.stderr.write(f'Usage: {sys.argv[0]} [-h] <status-url to monitor>\n')
    sys.exit(98)

url = sys.argv[1]
dom = url.replace("https://","").replace("http://","")

html_text = requests.get(url).text
soup = BeautifulSoup(html_text, 'html.parser')
ok = True
alt = {}

if __name__ == '__main__':
    attr = {
        'class': re.compile(r'|name|component-status|ago|unresolved-incident|incident-title'),
    }
    name,status,incident = "","",[]
    for a in soup.find_all(['a'], attrs=attr):
        if ('actual-title' in a["class"]):
              incident.append(a.text.strip(' \n\t\r').replace("\n",""))

    for tag in soup.find_all(['span','div'], attrs=attr):
        if ('name' in tag["class"]):
            status = ""
            name = tag.text.strip(' \n\t\r').replace("\n","")
        if ('component-status' in tag["class"]):
            status = tag.text.strip(' \n\t\r').replace("\n","")
            if status not in alt:
                alt[status] = []
            alt[status].append(name)
            if status != "Operational":
                ok = False

if not ok:
    print(f"CRITICAL {dom} - ", end = "")
    print(" ".join(incident).strip(), sep = ", ", end = "")

for status in alt:
    if status != "Operational":
        print(f" {status.upper()}: ", end = "")
        print(' '.join(alt[status]).strip(), sep = ", ", end = "")

if ok:
    print(f"OK {dom} - Operational")
    sys.exit(0)
else:
    print()
    sys.exit(2)
