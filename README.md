# Fabrik-Betriebssystem – Referenzimplementierung 0.22.0

## Release
0.22.0 – Verteilte Konsistenz und robuste Ereignisverarbeitung.

### Kern des Releases
- persistenter Ausgabepuffer (Outbox)
- persistenter Eingangsschutz (Inbox)
- Lease-basierte Übernahme und Wiederübernahme
- Bestätigung nur durch gültigen Lease-Besitzer
- zentrale Produktionskonfiguration und Composition Root
- austauschbarer Nachrichtenbroker mit lokaler Referenz und optionalem Redis-Adapter
- Gesundheits- und Bereitschaftsprüfung
- Datenbankverbindung über `FABRIK_DATENBANK_URL`
- persistente Governance-/Laufzeitmodelle aus den vorherigen Versionen
- öffentliche `/gesundheit`- und `/bereitschaft`-Endpunkte
- konsistente Paket-/API-Version 0.18.0

### Konfigurationsvariablen
- `FABRIK_DATENBANK_URL`
- `FABRIK_UMGEBUNG`
- `FABRIK_INSTANZKENNUNG`
- `FABRIK_MAXIMALE_WIEDERHOLUNGEN`

### Prüfung
- 40/40 Tests bestanden
- Python-Kompilierungsprüfung bestanden
- lokaler Demo-Lauf bestanden

### Statusgrenze
PostgreSQL, Redis und externe Identitätsdienste sind als Zielintegrationen vorbereitet, wurden in dieser isolierten Umgebung jedoch nicht gegen reale externe Dienste ausgeführt.


## 0.20.0 – Betriebs- und Bereitstellungsrelease
- getrennte API-, Worker- und Ablaufplaner-Startbefehle
- Dockerfile und Docker Compose mit PostgreSQL und Redis
- CI-Prüfkette für Python 3.11–3.13
- dokumentierter SQL-Migrationsstarter
- Ende-zu-Ende-HTTP-Prüfung
- Konfiguration über Umgebungsvariablen

### Statusgrenze
PostgreSQL/Redis-Container und externe CI-Plattformen sind in der isolierten Umgebung nicht gestartet worden. Die lokale Referenzsuite wurde ausgeführt.


## Version 0.22.0 – verteilte Konsistenz

Neu implementiert:
- transaktionaler Ausgabepuffer mit datenbankbasiertem Lease
- dauerhafter Inbox-Schutz gegen doppelte Konsumierung
- Wiederübernahme nach abgelaufenem Lease
- Bestätigung nur durch den gültigen Lease-Besitzer
- Normalisierung von naiven/UTC-Zeitstempeln
- zentrale Anwendung bindet Inbox und Ausgabepuffer ein

Prüfung: 52/52 Tests bestanden; Python-Kompilierung bestanden; Demo als Modul erfolgreich.
