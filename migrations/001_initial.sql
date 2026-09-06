-- Fabrik-Betriebssystem 0.19.0
-- Diese Migration dokumentiert die kanonische Initialstruktur.
-- Die Python-Referenzimplementierung kann weiterhin create_all für lokale Entwicklung verwenden.
CREATE TABLE IF NOT EXISTS migrationsstand (
    migrationskennung VARCHAR(255) PRIMARY KEY,
    version VARCHAR(32) NOT NULL,
    angewendet_am TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO migrationsstand (migrationskennung, version)
VALUES ('fabrik-betriebssystem', '0.19.0')
ON CONFLICT (migrationskennung) DO UPDATE SET version = EXCLUDED.version, angewendet_am = CURRENT_TIMESTAMP;
