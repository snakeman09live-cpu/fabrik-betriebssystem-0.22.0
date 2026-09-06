# Fabrik-Betriebssystem – Referenzimplementierung 0.22.0

Referenzimplementierung eines Fabrik-Betriebssystems mit persistenter
Zustandsführung, verteilter Konsistenz und ereignisgetriebener Verarbeitung.

## Installation

```bash
python -m venv .venv
.venv/Scripts/activate        # Linux/macOS: source .venv/bin/activate
pip install -e ".[test]"
```

## Start

```bash
fabrik-api                    # HTTP-Schnittstelle
fabrik-worker                 # Aufgabenverarbeitung
fabrik-ablaufplaner           # Ablaufplanung
```

Alternativ das vollständige Gespann mit PostgreSQL und Redis:

```bash
docker compose up
```

## Konfigurationsvariablen

| Variable | Bedeutung |
| --- | --- |
| `FABRIK_DATENBANK_URL` | Datenbankverbindung (Standard: lokales SQLite) |
| `FABRIK_UMGEBUNG` | Betriebsumgebung, z. B. `PRODUKTION` |
| `FABRIK_INSTANZKENNUNG` | Kennung der laufenden Instanz für Lease-Besitz |
| `FABRIK_MAXIMALE_WIEDERHOLUNGEN` | Obergrenze für Wiederholungsversuche |
| `FABRIK_REDIS_URL` | Broker-Adresse, wenn der Redis-Adapter genutzt wird |
| `FABRIK_DB_PASSWORT` | Datenbankpasswort für `docker compose` (Standard: `fabrik`) |

## Öffentliche Endpunkte

- `/gesundheit` – Lebendigkeitsprüfung
- `/bereitschaft` – Bereitschaftsprüfung

---

# Versionsverlauf

## 0.22.0 – Verteilte Konsistenz und robuste Ereignisverarbeitung

- transaktionaler Ausgabepuffer (Outbox) mit datenbankbasiertem Lease
- dauerhafter Eingangsschutz (Inbox) gegen doppelte Konsumierung
- Lease-basierte Übernahme und Wiederübernahme nach abgelaufenem Lease
- Bestätigung nur durch den gültigen Lease-Besitzer
- Normalisierung von naiven und UTC-Zeitstempeln
- zentrale Anwendung bindet Inbox und Ausgabepuffer ein
- Paket- und API-Version konsistent auf 0.22.0; die API liest die Version
  aus `fabrik_betriebssystem.__version__`, damit sie nicht erneut abdriftet

## 0.20.0 – Betriebs- und Bereitstellungsrelease

- getrennte API-, Worker- und Ablaufplaner-Startbefehle
- Dockerfile und Docker Compose mit PostgreSQL und Redis
- CI-Prüfkette für Python 3.11–3.13
- dokumentierter SQL-Migrationsstarter
- Ende-zu-Ende-HTTP-Prüfung
- Konfiguration über Umgebungsvariablen

## 0.18.0 – Produktionskern

- zentrale Produktionskonfiguration und Composition Root
- austauschbarer Nachrichtenbroker mit lokaler Referenz und optionalem
  Redis-Adapter
- Gesundheits- und Bereitschaftsprüfung
- Datenbankverbindung über `FABRIK_DATENBANK_URL`
- persistente Governance- und Laufzeitmodelle

---

## Prüfung

Der aktuelle Prüfstand ist in [RELEASE_STATUS.md](RELEASE_STATUS.md)
dokumentiert.

## Statusgrenze

PostgreSQL, Redis und externe Identitätsdienste sind als Zielintegrationen
vorbereitet, wurden in der isolierten Entwicklungsumgebung jedoch nicht gegen
reale externe Dienste ausgeführt. Die lokale Referenzsuite wurde ausgeführt.
