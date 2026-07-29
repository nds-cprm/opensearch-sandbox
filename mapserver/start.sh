#!/bin/bash
spawn-fcgi -n -f ${NUM_WORKERS} -p 9000 /usr/lib/cgi-bin/mapserv
