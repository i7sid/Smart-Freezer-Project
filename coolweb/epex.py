from lxml import html
import re
import datetime
import requests

# http://www.epexspot.com/de/marktdaten/auktionshandel

def parse_epex():
    r = requests.get('http://www.epexspot.com/de/marktdaten/auktionshandel')
    tree = html.fromstring(r.text)

    res = {}

    for row in range(3, 10):
        date = tree.xpath('//*[@id="tab_fr"]/table[3]/tbody/tr[1]/th[' + str(row) + ']/text()')
        m = re.search(', ([\d]*).([\d]*)', str(date))
        dateParsed = str(datetime.datetime.now().year) + '-' + m.group(2) + '-' + m.group(1)

        res[dateParsed] = {}

        for hour in range(0, 24):
            price = tree.xpath('//*[@id="tab_fr"]/table[3]/tbody/tr[' + str(2 + hour * 2) + ']/td[' + str(row) + ']/text()')
            res[dateParsed][hour] = float(str(price[0]).replace(",", "."))

    #prices = OrderedDict(sorted(res.items(), key=lambda t: t[0]))

    kwh = 26.50

    retPrices = {}

    for day in res.keys():
        prices = res[day]
        maxPrice = max(prices.values())
        minPrice = min(prices.values())

        for k in prices.keys():
            prices[k] -= minPrice
            #prices[k] /= maxPrice - minPrice

        avg = sum(prices.values()) / len(prices)

        for k in prices.keys():
            prices[k] += kwh - avg

        for k in prices.keys():
            prices[k] = (prices[k] - kwh) * 0.75 + kwh

        for k in prices.keys():
            prices[k] = round(prices[k], 2)

        retPrices[day] = prices

    return retPrices
