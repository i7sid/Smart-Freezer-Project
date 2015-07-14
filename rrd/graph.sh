#!/bin/sh
rrdtool graph /data/temp_graph.png \
	-w 785 -h 120 -a PNG \
	--slope-mode \
	--start -7200 --end now \
	--vertical-label "temperature (°C)" \
	DEF:tempInside=/data/temp.rrd:tempInside:MAX \
	LINE1:tempInside#ff0000:"temp inside" \

