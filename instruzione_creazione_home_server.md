# QuitStats

Web app Flask per il monitoraggio delle sigarette, con dashboard personale,
codice amico e supporto tra utenti.

## Deploy con Docker Compose

Da una directory del server che contiene il progetto:

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
# Inserire il valore prodotto in SECRET_KEY dentro .env

docker compose up -d --build
docker compose ps
docker compose logs -f quitstats
```

Il database SQLite viene salvato nel volume Docker `quitstats-data`, separato
dal container e quindi conservato durante gli aggiornamenti dell'immagine.

Per verificare il servizio:

```bash
curl http://127.0.0.1:5000/health
```

La risposta attesa è:

```json
{"status":"ok"}
```

## Nginx Proxy Manager

Creare un Proxy Host con:

- **Domain Names:** `tommi-webapp.servemp3.com`
- **Scheme:** `http`
- **Forward Hostname / IP:** indirizzo IP del container LXC Docker
- **Forward Port:** `5000` (oppure il valore di `QUITSTATS_PORT`)
- **Websockets Support:** attivo

Configurare il certificato SSL Let's Encrypt in Nginx Proxy Manager e attivare
Force SSL. Con HTTPS, mantenere `SESSION_COOKIE_SECURE=1`.

## Backup SQLite

Il volume contiene il database in `/app/data/quitstats.db`. Per un backup
semplice e coerente:

```bash
docker compose exec quitstats python -c \
  "import sqlite3; c=sqlite3.connect('/app/data/quitstats.db'); c.execute(\"VACUUM INTO '/app/data/quitstats-backup.db'\"); c.close()"
docker cp quitstats:/app/data/quitstats-backup.db ./quitstats-backup.db
```

Conservare il file di backup fuori dal container e testare periodicamente il
ripristino su una copia separata.
