import re

def parse_pca301():
    temp = {}

    lines = open("/opt/fhem/log/PCA301_0C3C27-2015.log").readlines()
    for line in lines:
        if line.find("power") == -1:
            continue
        m = re.search("([^_]*)_([\d]*):.*power: ([\d.]*).*", line)

        date = m.group(1) + "_" + m.group(2)
        if date in temp.keys():
            tmp = temp[date]
            tmp["sum"] = tmp["sum"] + float(m.group(3))
            tmp["num"] = tmp["num"] + 1
            tmp["total"] = tmp["sum"] / 60
            temp[date] = tmp
        else:
            tmp = {}
            tmp["sum"] = float(m.group(3))
            tmp["num"] = 1
            tmp["total"] = float(m.group(3))
            temp[date] = tmp

    ret = {}

    for date_hour in temp:
        m = re.search("([^_]*)_([\d]*)", date_hour)
        date = m.group(1)
        hour = m.group(2)
        if date not in ret.keys():
            ret[date] = {}
        ret[date][hour] = temp[date_hour]

    return ret

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
