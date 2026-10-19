# QuitStats - Self-Hosted Smoking Cessation & Cigarette Tracker

> **Un dato alla volta, con il supporto delle persone che contano.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![PWA](https://img.shields.io/badge/PWA-ready-5A0FC8?logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

QuitStats è una Web App self-hosted per registrare il consumo di sigarette,
osservare l'andamento nel tempo e condividere statistiche in sola lettura con
una persona di fiducia.

Il caso d'uso principale è un'installazione personale su un server domestico,
ad esempio un container LXC Docker su Proxmox, pubblicata tramite Nginx Proxy
Manager. Non è richiesto un server mail: autenticazione, collegamento tra
utenti e dati applicativi funzionano interamente tramite l'applicazione e il
database SQLite locale.

## Funzionalità Core

### Dashboard Fumatore

Un account con ruolo `fumatore` può:

- registrare una sigaretta con un solo tap/click;
- visualizzare il conteggio di oggi;
- vedere statistiche mensili e complessive;
- consultare totale e media giornaliera della settimana;
- visualizzare il grafico dell'andamento settimanale;
- vedere le sigarette registrate oggi con il relativo orario;
- rimuovere una singola registrazione inserita per errore.

Lo stesso account può anche sostenere un altro fumatore: il ruolo descrive il
profilo principale, non impedisce l'utilizzo del modulo di supporto.

### Modulo Sostenitore — Codice Amico

Un fumatore può generare un codice amico di sei caratteri composto da lettere
maiuscole e numeri. Il codice viene generato tramite `secrets.choice` e
memorizzato con vincolo `UNIQUE` nella tabella `users`; l'associazione non
dipende da email, SMTP o inviti via link.

Un utente autenticato, sia con ruolo `sostenitore` sia con ruolo `fumatore`, può
inserire il codice di un altro fumatore. Il collegamento salva il suo
`supported_user_id` e consente di visualizzare le statistiche del fumatore
supportato esclusivamente in sola lettura:

- oggi;
- mese corrente;
- totale assoluto;
- totale e media giornaliera della settimana;
- grafico settimanale.

L'applicazione impedisce inoltre di collegare il proprio codice amico a se
stessi.

### PWA Ready

QuitStats include:

- `static/manifest.json` con modalità `standalone`;
- `static/service-worker.js` per la cache dell'App Shell;
- layout responsive mobile-first;
- installabilità su dispositivi mobili e desktop dai browser compatibili;
- fruizione a schermo intero dopo l'installazione.

Il Service Worker mette in cache la home, il CSS, il JavaScript e il manifest.
Le richieste API non vengono servite dalla cache, così le statistiche restano
legate ai dati correnti del server.

## Stack Tecnologico & Architettura

### Backend

- Python 3.10 o superiore;
- Flask 3.x;
- Flask-SQLAlchemy 3.x;
- Werkzeug Security per hashing e verifica delle password;
- Gunicorn per l'esecuzione in produzione tramite Docker;
- sessioni Flask con cookie `HttpOnly`, `SameSite=Lax` e, in produzione HTTPS,
  `Secure`.

### Storage

SQLite è il database single-node dell'applicazione. In esecuzione Docker il
file viene scritto in:

```text
/app/data/quitstats.db
```

Il percorso `/app/data` è persistito nel volume Docker nominato
`quitstats-data`, esterno al filesystem effimero del container. Questo mantiene
il database disponibile durante ricreazione e aggiornamento dell'immagine.

In esecuzione locale, in assenza di `DATABASE_URL`, Flask-SQLAlchemy utilizza:

```text
sqlite:///quitstats.db
```

### Frontend

- HTML server-rendered tramite Jinja;
- CSS nativo responsive mobile-first;
- JavaScript vanilla per autenticazione, navigazione, statistiche e azioni;
- Web App Manifest;
- Service Worker.

### Infrastruttura

- Docker con immagine `python:3.12-slim`;
- Docker Compose;
- processo Gunicorn non-root con due worker;
- health check su `/health`;
- predisposizione per reverse proxy Nginx Proxy Manager;
- terminazione SSL tramite certificato Let's Encrypt su Nginx Proxy Manager.

## Struttura del Repository

```text
quitstats/
├── app.py                         # Application factory Flask, sessioni e API
├── databases.py                   # Modelli SQLAlchemy e inizializzazione db
├── requirements.txt               # Dipendenze Python runtime
├── Dockerfile                     # Immagine di produzione Gunicorn
├── docker-compose.yml             # Servizio, volume SQLite e health check
├── .env.example                   # Variabili d'ambiente documentate
├── .dockerignore                  # File esclusi dal build context Docker
├── .gitignore                     # Segreti, database, cache e file locali
├── LICENSE                        # Licenza MIT
├── README.md                      # Documentazione del progetto
├── templates/
│   └── index.html                 # Shell HTML della Web App
└── static/
    ├── css/
    │   └── app.css                # Stili responsive e componenti UI
    ├── js/
    │   └── app.js                 # Stato frontend e chiamate API
    ├── manifest.json              # Metadata installazione PWA
    └── service-worker.js          # Cache dell'App Shell
```

Le directory locali `venv/`, `instance/`, `data/` e i file SQLite possono
esistere nell'ambiente di sviluppo o sul server, ma sono esclusi dal repository
tramite `.gitignore`.

## API e Modelli

### Rotte HTTP

| Metodo | Rotta | Autorizzazione | Scopo |
|---|---|---|---|
| `GET` | `/` | Pubblica | Serve la Web App |
| `GET` | `/health` | Pubblica | Health check Docker |
| `POST` | `/api/auth/register` | Pubblica | Registra account e crea la sessione |
| `POST` | `/api/auth/login` | Pubblica | Autentica account |
| `POST` | `/api/auth/logout` | Autenticato | Termina la sessione |
| `GET` | `/api/auth/me` | Autenticato | Restituisce l'utente corrente |
| `POST` | `/api/smoker/cigarettes` | `fumatore` | Registra una sigaretta |
| `DELETE` | `/api/smoker/cigarettes/<cigarette_id>` | `fumatore` | Rimuove una propria sigaretta |
| `GET` | `/api/smoker/stats` | `fumatore` | Restituisce statistiche personali |
| `POST` | `/api/smoker/friend-code` | `fumatore` | Genera o restituisce il codice amico |
| `POST` | `/api/supporter/connect` | Autenticato | Collega l'utente a un fumatore |
| `GET` | `/api/supporter/dashboard` | Autenticato | Restituisce statistiche del sostenuto |

### Modelli database

#### `users`

- `id`: chiave primaria intera;
- `username`: username univoco;
- `password_hash`: password hashata, mai salvata in chiaro;
- `role`: `fumatore` oppure `sostenitore`;
- `friend_code`: codice amico opzionale e univoco di sei caratteri;
- `supported_user_id`: foreign key ricorsiva verso `users.id`.

#### `cigarettes`

- `id`: chiave primaria intera;
- `user_id`: foreign key verso `users.id`;
- `timestamp`: data e ora UTC della registrazione.

Le sigarette vengono eliminate in cascata quando viene eliminato l'utente. Se
un utente supportato viene eliminato, il collegamento del sostenitore viene
impostato a `NULL`.

## Installazione e Avvio Rapido

### Prerequisiti

Per il deploy raccomandato:

- Linux o un host compatibile con Docker;
- Docker Engine;
- Docker Compose V2 (`docker compose`) oppure Docker Compose legacy
  (`docker-compose`);
- accesso alla porta host `5000`, o a una porta alternativa configurata.

Per lo sviluppo locale:

- Python 3.10 o superiore;
- `venv`;
- pip.

### Configurazione `.env`

Creare il file locale partendo dall'esempio:

```bash
cp .env.example .env
```

Generare una chiave casuale con il modulo standard Python:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Inserire il valore generato in `.env`:

```dotenv
SECRET_KEY=valore-casuale-generato
SESSION_COOKIE_SECURE=1
SESSION_LIFETIME_DAYS=30
QUITSTATS_PORT=5000
```

Parametri disponibili:

- `SECRET_KEY`: chiave obbligatoria per firmare le sessioni Flask. Deve essere
  lunga, casuale e privata.
- `SESSION_COOKIE_SECURE`: usare `1` quando l'app è esposta tramite HTTPS;
  usare `0` solo per sviluppo locale in HTTP.
- `SESSION_LIFETIME_DAYS`: durata, in giorni, della sessione quando l'utente
  seleziona `Rimani connesso` durante il login. Il default è `30`.
- `QUITSTATS_PORT`: porta pubblicata sull'host e utilizzata da Nginx Proxy
  Manager per raggiungere il container. Il default è `5000`.

Il file `.env` è escluso da Git. Non inserire mai chiavi reali in
`docker-compose.yml`, `.env.example`, issue o documentazione pubblica.

### Deploy con Docker — raccomandato per produzione

Dalla root del repository:

```bash
cp .env.example .env
# Modificare SECRET_KEY dentro .env

docker compose up -d --build
docker compose ps
docker compose logs -f quitstats
```

Con Docker Compose legacy:

```bash
docker-compose up -d --build
docker-compose ps
docker-compose logs -f quitstats
```

Verificare il servizio localmente:

```bash
curl http://127.0.0.1:5000/health
```

Risposta attesa:

```json
{"status":"ok"}
```

Per fermare il servizio senza eliminare i dati:

```bash
docker compose stop
```

Per ricrearlo dopo un aggiornamento del codice:

```bash
docker compose up -d --build
```

Non usare `docker compose down -v` se si vuole conservare il database: il
comando rimuove anche il volume `quitstats-data`.

### Esecuzione locale — ambiente di sviluppo

Creare e attivare un virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Installare le dipendenze:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Avviare Flask in sviluppo:

```bash
python app.py
```

L'app sarà disponibile su:

```text
http://127.0.0.1:5000/
```

Per usare un database locale esplicito:

```bash
export DATABASE_URL="sqlite:///quitstats.db"
export SECRET_KEY="chiave-locale-di-sviluppo"
python app.py
```

In sviluppo HTTP impostare:

```bash
export SESSION_COOKIE_SECURE=0
```

## Deployment dietro Nginx Proxy Manager

Per il dominio previsto `tommi-webapp.servemp3.com`, creare un Proxy Host con:

- **Domain Names:** `tommi-webapp.servemp3.com`
- **Scheme:** `http`
- **Forward Hostname / IP:** IP del container LXC che esegue Docker
- **Forward Port:** `5000`, oppure il valore di `QUITSTATS_PORT`
- **Websockets Support:** attivo

Configurare in Nginx Proxy Manager un certificato Let's Encrypt e attivare
`Force SSL`. Poiché l'app riceverà traffico pubblico in HTTPS, mantenere
`SESSION_COOKIE_SECURE=1`.

Il container ascolta sulla rete Docker e la porta pubblicata sull'host è il
punto di ingresso usato dal reverse proxy. Non esporre direttamente il
database SQLite o la porta del container su Internet senza il reverse proxy e
HTTPS.

## Manutenzione e Backup

### Backup del database SQLite

Il database di produzione è nel volume Docker nominato `quitstats-data`, al
percorso `/app/data/quitstats.db`. Creare un backup coerente con SQLite:

```bash
docker compose exec quitstats python -c \
  "import sqlite3; c=sqlite3.connect('/app/data/quitstats.db'); c.execute(\"VACUUM INTO '/app/data/quitstats-backup.db'\"); c.close()"
docker cp quitstats:/app/data/quitstats-backup.db ./quitstats-backup.db
```

Con Compose legacy sostituire `docker compose` con `docker-compose` nel primo
comando.

Conservare `quitstats-backup.db` fuori dal container e in una posizione
protetta. Il file è un database applicativo e può contenere dati personali.

In alternativa, per archiviare il volume Docker:

```bash
docker run --rm \
  -v quitstats-data:/source:ro \
  -v "$PWD/backups:/backup" \
  alpine tar czf /backup/quitstats-data.tar.gz -C /source .
```

Non includere i backup nel repository Git. La directory `backups/` dovrebbe
essere aggiunta alle regole locali di esclusione se viene usata sul server.

### Aggiornamento applicazione

```bash
docker compose up -d --build
docker compose ps
```

Prima di aggiornamenti importanti, creare un backup del volume SQLite.

## Licenza

QuitStats è distribuito con licenza **MIT**. Il testo completo è disponibile
nel file [LICENSE](./LICENSE).
