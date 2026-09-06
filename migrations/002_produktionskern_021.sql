-- Fabrik-Betriebssystem 0.21.0
-- Transaktionale Ausgabepuffer-Tabelle für das Outbox-Muster.
CREATE TABLE IF NOT EXISTS ausgabepuffer (
    kennung VARCHAR(255) PRIMARY KEY,
    kanal VARCHAR(255) NOT NULL,
    nutzlast TEXT NOT NULL,
    erstellt_am TIMESTAMP NOT NULL,
    bestaetigt BOOLEAN NOT NULL DEFAULT FALSE,
    bestaetigt_am TIMESTAMP NULL
);
CREATE INDEX IF NOT EXISTS ix_ausgabepuffer_offen
    ON ausgabepuffer (bestaetigt, erstellt_am);
