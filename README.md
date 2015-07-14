# Smart-Freezer project

## Komponenten

### displayserver

Zuständig für die Kommunikation mit dem Display (EA DOGM204-A) über die SPI-Schnittstelle.

Anschluss über die PINs 17 (VCC-3.3V), 19 (SPI0_MOSI), 21 (SPI0_MISO), 23 (SPI0-CLK), 25 (GND), Nutzung der Chip-Select-Leitungen nicht implementiert

Kommunikation über ZeroMQ

Zwei Arten von Display-Messages:
* Flash-Messages: begrenzte Anzeigedauer (für interaktive Ineraktion, z.B. für den Fingerprint-Sensor)
* Standby-Messages: Für Status-Informationen (z.B. Temperatur-Werte)

Dämon ausführen:
```shell
python DisplayServer.py
```

Beispiel-Client:
```shell
python DisplayClient.py
```

### tempctrld Temperatur-Controller

Temperatur-Regler um die Temperatur konstant zu halten.

Hinweis: Watchdog-Modul aktuell nur für Raspberry PI implementiert

Konfiguration über die Variablen in der Klasse TempController

1-Wire-Temperatur-Sensoren sind wie auf
http://www.einplatinencomputer.com/banana-pi-1-wire-temperatursensor-ds1820-ansteuern/
beschrieben angeschlossen.

Relais für Kühlaggregat hängt an GPIO-Pin 17.

Kommunikation mit der Außenwelt über:
* /run/shm/temp.outside: Temperatur außerhalb des Kühlschrankes
* /run/shm/temp.inside: Temperatur im Kühlschrank
* /run/shm/temp.set: aktuelle Regeltemperatur (maximale Temperatur)
* /run/shm/temp.wish: Darüber kann eine neue Wunsch-Temperatur gesetzt werden.

Dämon ausführen:
```shell
python TempController.py
```

### pictured

Erstellt sekündlich mit der ansgeschlossenen USB-Webcam Fotos, sobal das Reed-Relais geöffnet ist.

Dämon ausführen:
```shell
python take_picture.py
```

### fingerprintd

Abrechnungs-System über den Fingerprint-Sensor GT-511C3.

Fingerprint-Sensor hängt an den PINs 4 (VCC-5V), 6 (GND), 8 (UART4_TX) und 10 (UART4-RX)

Kommuniziert über ZeroMQ mit dem displayserver.

Stellt über ZeroMQ eine Schnittstelle für das Web-Interface (coolweb) zur Verfügung.

Dämon ausführen:
```shell
python FingerprintService.py
```

### coolweb

Verwendetes Framework: Python Flask

Web-Interface zur Kontrolle/Steuerung des Temperatur-Reglers, Anbindung an die Energiebörse EPEX, Parsing des Energiekostenmonitors PCA 301 über FHEM/JeeLink.

Dämon ausführen:
```shell
python coolweb.py
```

## Crontab + RRDtool Konfiguration
```
* * * * * rrdtool update /data/temp.rrd N:`cat /run/shm/temp.inside`:`/opt/kuehlschrank/energy.sh`
* * * * * sh /opt/kuehlschrank/rrd/graph.sh > /dev/null
* * * * * sh /opt/kuehlschrank/rrd/graph2.sh > /dev/null
```

### Erstellung RRD Datei
```shell
rrdtool create temp.rrd --step 5 DS:tempInside:GAUGE:600:-50:30 DS:energy:GAUGE:600:0:500 RRA:MAX:0.5:1:1440
```

### graph.sh:
