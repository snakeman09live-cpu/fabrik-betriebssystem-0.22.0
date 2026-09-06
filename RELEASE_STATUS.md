# Release-Status 0.22.0

## Tatsächlich geprüft
- 52/52 Tests bestanden
- Python-Kompilierung bestanden
- Demo-Lauf bestanden
- Release-Archiv geprüft

Nachgeprüft am 2026-09-06 unter Python 3.14.7 (Windows): 52/52 Tests bestanden,
Kompilierung aller Module bestanden, Demo-Lauf bestanden. Die CI-Kette prüft
bislang nur Python 3.11–3.13.

## Nachträgliche Korrekturen am Archivstand
- Paketerkennung: `pyproject.toml` deklariert `packages` nun explizit. Ohne
  diese Angabe brach `pip install -e .` mit einem Discovery-Fehler ab, das
  Archiv war nicht installierbar.
- Versionsangaben: `__init__.py` (war 0.21.0) und die FastAPI-Anwendung
  (war 0.18.0) liegen nun konsistent bei 0.22.0; die API leitet ihre Version
  aus `__version__` ab.
- `docker-compose.yml`: Datenbankpasswort über `FABRIK_DB_PASSWORT`
  überschreibbar, Standardwert unverändert.

## Lokal verifiziert
- SQLite-basierte Persistenz
- Outbox-/Inbox-Logik
- Lease-Übernahme und Wiederübernahme
- Idempotenz-/Duplikatschutz
- Zustandsversionsschutz
- Ereigniskonsistenz

## Noch nicht gegen echte externe Dienste ausgeführt
- PostgreSQL-Server
- Redis-Server
- externe CI-Plattform
- externe Identitätsdienste
- produktive Container-Orchestrierung

## Versionsgrenze
Der Inhalt dieses Archivs entspricht der Referenzimplementierung 0.22.0.
Veröffentlichte Versionen sind konzeptionell unveränderlich; Änderungen erzeugen eine neue Version.
