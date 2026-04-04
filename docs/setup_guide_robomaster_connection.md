Einrichtungsanleitung: DJI Robomaster EP Core — WLAN-Verbindung (STA-Modus)

Diese Anleitung beschreibt Schritt für Schritt, wie man den DJI Robomaster über den STA-Modus (WLAN-Router-Modus) mit einem Laptop verbindet und die Verbindung per Python testet. 
In dieser Anleitung wird der DJI Robomaster ep core als Standard verwendet.









Inhaltsverzeichnis

Einrichtungsanleitung: DJI Robomaster EP Core — WLAN-Verbindung (STA-Modus)	1
Inhaltsverzeichnis	1
1. Voraussetzungen	2
2. Überblick: Verbindungsmodi	2
3. STA-Modus einrichten	3
4. Python-Umgebung vorbereiten	4
5. Verbindung testen	5
6. Fehlerbehebung	6





1. Voraussetzungen

Hardware
DJI Robomaster EP Core (eingeschaltet und geladen)
Laptop mit WLAN-Fähigkeit
WLAN-Router 
Smartphone mit der DJI Robomaster App (für die Ersteinrichtung)

Software
Python 3.6.5 – 3.8.x (empfohlen: Python 3.8)
DJI Robomaster App 

Wichtige Hinweise
Der Roboter, der Laptop und das Smartphone müssen sich im selben WLAN-Netzwerk befinden.



2. Überblick: Verbindungsmodi

Der Robomaster EP Core unterstützt drei Verbindungsmodi:
Modus
Beschreibung
Anwendungsfall
AP (Access Point)
Der Roboter öffnet ein eigenes WLAN. Der Laptop verbindet sich direkt damit.
Schnelltests ohne Router
STA (Station/Router)
Der Roboter verbindet sich mit einem bestehenden WLAN-Router.
Empfohlen für die Entwicklung
RNDIS (USB)
Verbindung über USB-Kabel.
Niedrigste Latenz, kabelgebunden



Wir verwenden den STA-Modus, da Laptop und Roboter im selben Netzwerk sind und der Laptop gleichzeitig Internetzugang behält.


3. STA-Modus einrichten

Schritt 3.1: Roboter einschalten
1. Den Akku in den Robomaster EP Core einsetzen.
2. Den Power-Knopf (an dem Akku) drücken und halten, bis der Roboter startet.
3. Warten, bis die LEDs am Roboter leuchten und der Roboter betriebsbereit ist.

Abbildung 1DJI Robomaster ep core Hintereaufnahme startknopf

Schritt 3.2: Verbindungsmodus am Roboter umschalten
1. Am Intelligent Controller (die zentrale Steuereinheit mit Antenne) den Modusschalter auf Networking-Modus (Router/STA) stellen.
2. Der Roboter ist jetzt bereit, sich mit einem WLAN-Router zu verbinden. Der Lautsprecher am Roboter sagt „QR-Code abscannen“, wenn nicht dann einmal den roten Knopf lange gedrückt halten bis der Roboter sich zurücksetzt und dann wieder den roten Knopf einmal drücken. Danach kommt von dem Lautsprecher „QR-Code abscannen“. 

Abbildung 2 DJI Robomaster ep core Seitenaufnahme Modusschlater und reset Knopf

Schritt 3.3: Smartphone mit dem WLAN verbinden
1. Das Smartphone mit dem gewünschten WLAN-Router verbinden.
2. Die DJI Robomaster App auf dem Smartphone öffnen.
3. oben in der App auf „connect“ drücken und dann „Connection via Router auswählen“
Danach wird ein QR-Code angezeigt, den vor die Kamera des Roboters halten, bis der Roboter die Verbindung bestätigt. 

Hinweis: Der QR-Code enthält die WLAN-Zugangsdaten. Der Roboter speichert diese und verbindet sich beim nächsten Einschalten automatisch mit dem Netzwerk, solange der Modus auf STA bleibt.

Schritt 3.4: Laptop mit demselben WLAN verbinden
Den Laptop mit demselben WLAN-Router verbinden, mit dem der Roboter verbunden ist. Beide Geräte müssen im selben Netzwerk sein.


4. Python-Umgebung vorbereiten
Für diese Anleitung wird PyCharm als IDE benutzt

Schritt 4.1: Python-Version prüfen
python --version
Erwartete Ausgabe: `Python 3.8.x` (oder 3.6.5 – 3.8.x)

Schritt 4.2: Virtuelle Umgebung erstellen (optional)
python -m venv venv
Aktivieren:
Windows (PowerShell): .\venv\Scripts\Activate.ps1
Windows (cmd): venv\Scripts\activate.bat
Linux / macOS: source venv/bin/activate

Schritt 4.3: Robomaster SDK installieren
pip install robomaster

Das installiert automatisch die Abhängigkeiten: "numpy", "opencv-python", "netaddr", "netifaces", "myqr".

Schritt 4.4: Installation überprüfen
python -c "import robomaster; print(robomaster.version.__version__)"

Es sollte die SDK-Versionsnummer ausgegeben werden.
5. Verbindung testen

Schritt 5.1: Schnelltest: Verbindung und Firmware-Version

Erstelle eine Datei z.B. „test_connection.py“:

from robomaster import robot

if __name__ == "__main__":
   ep_robot = robot.Robot()
   ep_robot.initialize(conn_type="sta")

   version = ep_robot.get_version()
   print("Verbindung erfolgreich!")
   print("Firmware-Version: {}".format(version))

   ep_robot.close()

Ausführen:
python test_connection.py

Erwartete Ausgabe:
Verbindung erfolgreich!
Firmware-Version: xx.xx.xx.xx

Weitere Testsbeispiele befinden sich in der robomaster SDK.

6. Fehlerbehebung

Problem: “ModuleNotFoundError: No module named 'robomaster'”

Das SDK ist nicht installiert. Lösung:
pip install robomaster

Falls eine virtuelle Umgebung verwendet wird, sicherstellen dass diese aktiviert ist.

Problem: QR-Code wird nicht erkannt
Den QR-Code **direkt und gerade** vor die Kamera halten (Abstand ca. 15–25 cm).
Gute Beleuchtung sicherstellen — kein Gegenlicht.
Bildschirmhelligkeit des Smartphones erhöhen.
Sicherstellen, dass die Kameralinse des Roboters sauber ist.





Weiterführende Ressourcen
- DJI Robomaster SDK: GitHub https://github.com/dji-sdk/RoboMaster-SDK 
- DJI Robomaster SDK: Dokumentation https://robomaster-dev.readthedocs.io/en/latest/ 
- DJI Robomaster SDK:  Testbeispiele https://github.com/dji-sdk/RoboMaster-SDK/tree/master/examples 
