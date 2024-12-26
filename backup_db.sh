#!/bin/bash

# Pfade zu den Datenbanken
OLD_DB="data/database.db"
SETUP_SQL="app/setup.sql"
BACKUP_DIR="backups" # Verzeichnis für Backups

# Erstelle das Backup-Verzeichnis, falls es nicht existiert
if [ ! -d "$BACKUP_DIR" ]; then
  mkdir "$BACKUP_DIR"
fi

# Erstelle einen Zeitstempel für das Backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup-Dateiname (nur den Dateinamen, ohne Pfad)
BACKUP_FILE="${BACKUP_DIR}/database.db_backup_${TIMESTAMP}.db"

# Überprüfe, ob die alte Datenbank existiert
if [ ! -f "$OLD_DB" ]; then
  echo "Alte Datenbank '$OLD_DB' nicht gefunden."
  exit 1
fi

# Erstelle ein Backup der alten Datenbank
echo "Erstelle Backup der alten Datenbank '$OLD_DB' nach '$BACKUP_FILE'..."
cp "$OLD_DB" "$BACKUP_FILE"

# Überprüfe, ob das Backup erfolgreich war
if [ $? -ne 0 ]; then
  echo "Fehler beim Erstellen des Backups."
  exit 1
fi

echo "Backup erfolgreich erstellt."
