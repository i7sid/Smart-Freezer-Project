#!/bin/sh
rrdtool graph /data/energy_graph.png \
	-w 785 -h 120 -a PNG \
	--slope-mode \
	--start -7200 --end now \
	--vertical-label "energy consumption (Wh)" \
	DEF:energy=/data/temp.rrd:energy:MAX \
	LINE1:energy#00ff00:"energy consumption" \

