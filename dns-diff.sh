#!/bin/bash

#
# Just for quick checking dns differences
#

# change datadir
DATADIR=/tmp/dnsdata
domain=domainname-example.org
dig axfr $domain +nostats > $DATADIR/$domain.$(date +%F.%s).txt
last=$(dir -atr1 $DATADIR/$domain* | tail -n1)
beforelast=$(dir -atr1 $DATADIR/$domain* | tail -n2 | head -n1)
diff -Naur $last $beforelast
