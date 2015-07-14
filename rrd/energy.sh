#!/bin/sh
awk '/power/{print $4}' /opt/fhem/log/PCA301_0C3C27-2015.log | tail -1

