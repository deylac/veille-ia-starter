# Installation manuelle — Étape par étape

Tutoriel complet pour installer le projet **sans** Claude Code. Si tu as Claude Code, préfère lancer la commande `/onboard` dans le repo cloné — Claude te guide à travers tout ça automatiquement (cf. [README.md](README.md)).

## Sommaire

1. [Prérequis machine](#1-prérequis-machine)
2. [Récupérer le code](#2-récupérer-le-code)
3. [Créer les comptes et obtenir les clés](#3-créer-les-comptes-et-obtenir-les-clés)
4. [Configuration locale](#4-configuration-locale)
5. [Créer la database Notion](#5-créer-la-database-notion)
6. [Configurer Gmail OAuth](#6-configurer-gmail-oauth)
7. [Setup Supabase + sous-pages Notion (rapports automatiques)](#7-setup-supabase--sous-pages-notion-rapports-automatiques)
8. [Test local](#8-test-local)
9. [Déploiement Railway](#9-déploiement-railway)
10. [Publier l'app Google Cloud en production](#10-publier-lapp-google-cloud-en-production)
11. [Vérification finale](#11-vérification-finale)

---

## 1. Prérequis machine

Tu dois avoir sur ta machine :

| Outil | Comment vérifier | Comment installer (macOS) |
|---|---|---|
| Python 3.11+ | `python3 --version` | `brew install python@3.11` |
| pip | `pip3 --version` | inclus avec Python |
| git | `git --version` | `brew install git` |
| Node.js (pour Railway CLI) | `node --version` | `brew install node` |
| Railway CLI | `railway --version` | `npm i -g @railway/cli` |
| gh CLI (optionnel, pour repo GitHub) | `gh --version` | `brew install gh` |

Linux : remplace `brew install` par `apt install` / `dnf install` selon ta distro.
Windows : télécharge les installers depuis les sites officiels ou utilise WSL2.

## 2. Récupérer le code

Tu as reçu le dossier `veille-ia-starter/` (par email, USB, ou téléchargement). Ouvre un terminal dedans :

```bash
cd chemin/vers/veille-ia-starter
```

Vérifie que tu vois bien les fichiers `main.py`, `requirements.txt`, etc. :

```bash
ls
```

## 3. Créer les comptes et obtenir les clés

Suis [ACCOUNTS_CHECKLIST.md](ACCOUNTS_CHECKLIST.md) dans l'ordre. À la fin tu as toutes les clés à coller dans `.env`.

**Ne passe pas à l'étape 4 avant d'avoir au minimum** : `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `NOTION_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`.

Gmail et Reddit peuvent être configurés plus tard (Gmail requis pour les newsletters, Reddit optionnel).

## 4. Configuration locale

### 4.1 Créer l'environnement virtuel Python

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# OU
.venv\Scripts\activate         # Windows PowerShell
```

Ton prompt shell doit maintenant afficher `(.venv)` devant.

### 4.2 Installer les dépendances

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Ça prend ~2-3 min (80+ paquets à installer).

### 4.3 Créer le fichier `.env`

Copie le template et ouvre-le dans ton éditeur :

```bash
cp .env.example .env
# puis édite .env avec VS Code, nano, ou ton éditeur
```

Remplis les valeurs avec les clés obtenues en étape 3 :

```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxx
OPENAI_API_KEY=sk-proj-xxxxxxxxx
GEMINI_API_KEY=AIzaSyXxxxxxxx
NOTION_API_KEY=ntn_xxxxxxxxx
NOTION_DATABASE_ID=34b76dcb9c4e803b9a13e75049aa7b8e
SUPABASE_URL=https://xxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJxxxxxxx
SUPABASE_BUCKET=veille-ia-images
```

## 5. Créer la database Notion

Tu as deux options :

### Option A — Via l'interface web Notion (manuel)

Dans ton workspace Notion :
1. Créer une nouvelle page vierge
2. Taper `/database` → choisir "Table - Inline"
3. Ajouter les 11 propriétés listées dans [ACCOUNTS_CHECKLIST.md — Notion](ACCOUNTS_CHECKLIST.md#4-notion--10-min)
4. Partager la database avec l'intégration "Veille IA Bot"
5. Copier le DATABASE_ID depuis l'URL → le coller dans `.env`

### Option B — Via script (rapide, zéro typo)

Note : cette option suppose que tu as déjà créé une page Notion vierge et que tu as partagé ton intégration avec cette page. Crée la database avec le script suivant. Copie-le dans un fichier `create_notion_db.py` à la racine :

```python
"""Crée automatiquement la database Notion avec les 11 propriétés."""
import os, json, requests
from dotenv import load_dotenv
load_dotenv('.env', override=True)

# Remplace par l'ID de la PAGE Notion parent que tu as créée et partagée avec l'intégration
PARENT_PAGE_ID = "COLLE_ICI_LID_DE_TA_PAGE_PARENT"

headers = {
    'Authorization': f"Bearer {os.getenv('NOTION_API_KEY')}",
    'Notion-Version': '2025-09-03',
    'Content-Type': 'application/json',
}

body = {
    "parent": {"type": "page_id", "page_id": PARENT_PAGE_ID},
    "title": [{"type": "text", "text": {"content": "Veille IA"}}],
    "is_inline": True,
    "properties": {
        "Titre": {"title": {}},
        "Image générée": {"type": "files", "files": {}},
        "Source": {"type": "select", "select": {"options": []}},
        "URL source": {"type": "url", "url": {}},
        "Score viral": {"type": "number", "number": {"format": "number"}},
        "Format utilisé": {
            "type": "select",
            "select": {"options": [
                {"name": "infographie", "color": "pink"},
                {"name": "carrousel", "color": "purple"},
                {"name": "annonce", "color": "blue"},
                {"name": "stat", "color": "green"},
                {"name": "citation", "color": "yellow"},
                {"name": "versus", "color": "orange"},
            ]},
        },
        "Hook suggéré FR": {"type": "rich_text", "rich_text": {}},
        "Angle éditorial": {"type": "rich_text", "rich_text": {}},
        "Statut": {
            "type": "select",
            "select": {"options": [
                {"name": "À valider", "color": "yellow"},
                {"name": "Validé", "color": "green"},
                {"name": "Rejeté", "color": "red"},
                {"name": "Publié", "color": "blue"},
            ]},
        },
        "Freelance assigné": {"type": "people", "people": {}},
        "Date scan": {"type": "date", "date": {}},
        "Type de document": {
            "type": "select",
            "select": {"options": [
                {"name": "infographie", "color": "blue"},
                {"name": "carrousel", "color": "pink"},
            ]},
        },
    },
}

r = requests.post("https://api.notion.com/v1/databases", headers=headers, json=body)
if r.status_code == 200:
    db = r.json()
    print(f"Database créée !")
    print(f"NOTION_DATABASE_ID = {db['id']}")
    print(f"URL : {db['url']}")
else:
    print(f"Erreur {r.status_code} :")
    print(json.dumps(r.json(), indent=2))
```

Lance-le :

```bash
python create_notion_db.py
```

Copie le `NOTION_DATABASE_ID` retourné dans ton `.env`.

## 6. Configurer Gmail OAuth

Prérequis : tu as déjà créé ton adresse Gmail dédiée + ton projet Google Cloud + téléchargé `gmail_credentials.json` (voir [ACCOUNTS_CHECKLIST.md — section 6](ACCOUNTS_CHECKLIST.md#6-gmail--google-cloud--20-min)).

Place le fichier téléchargé ici :

```bash
mv ~/Downloads/client_secret_xxxxx.json config/gmail_credentials.json
```

Lance le script d'OAuth (il ouvre un navigateur) :

```bash
python setup_gmail.py
```

Une fenêtre navigateur s'ouvre :
1. Connecte-toi avec l'adresse Gmail dédiée
2. Clique "Continue" sur l'écran "Google n'a pas validé"
3. Autorise l'accès → "The authentication flow has completed"

Le fichier `config/gmail_token.json` est créé automatiquement.

### Adapter la liste des expéditeurs newsletters

Le projet est préconfiguré avec une liste par défaut dans `config/settings.py` sous `NEWSLETTER_SENDERS`. Adapte-la aux expéditeurs que **tu reçois réellement**. Pour les identifier :

```python
# Dans un shell Python (.venv activé)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

creds = Credentials.from_authorized_user_file('config/gmail_token.json', ['https://www.googleapis.com/auth/gmail.readonly'])
if creds.expired: creds.refresh(Request())
service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
results = service.users().messages().list(userId='me', maxResults=20).execute()
for m in results.get('messages', []):
    msg = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From', 'Subject']).execute()
    h = {h['name']: h['value'] for h in msg['payload']['headers']}
    print(f"From: {h.get('From')[:60]}  |  Subj: {h.get('Subject', '')[:60]}")
```

Récupère les adresses email entre `<...>` et adapte `NEWSLETTER_SENDERS` dans `config/settings.py`.

## 7. Setup Supabase + sous-pages Notion (rapports automatiques)

À chaque run, le pipeline publie automatiquement dans Notion **2 sous-pages** :
- 🗞️ **Rapport quotidien** : détail du run du jour + 6 jours en historique (toggles).
  Si 0 image n'a été publiée, la page explique pourquoi (rejet scoring, etc.) — pas un bug.
- 💰 **Coûts API** : suivi des coûts journaliers + projection mensuelle.

### 7.1 Appliquer les migrations SQL Supabase

Va dans Supabase → SQL Editor → New query, et colle successivement le contenu de :
- `observability/migrations/001_api_calls.sql` (table `api_calls`)
- `observability/migrations/002_daily_runs.sql` (table `daily_runs`)

Clique **Run** pour chacune. Vérifie dans Table Editor que les 2 tables apparaissent.

### 7.2 Récupérer l'ID de la page Notion parente

Crée (ou identifie) la page Notion qui hébergera les 2 sous-pages. Partage-la avec ton intégration "Veille IA" (⋯ → Connections → Veille IA). Copie son ID (32 chars dans l'URL) dans `.env` :

```bash
NOTION_PARENT_PAGE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 7.3 Créer les 2 sous-pages

```bash
python setup_cost_report_page.py
# → copie l'ID retourné dans .env à NOTION_COST_REPORT_PAGE_ID

python setup_daily_report_page.py
# → copie l'ID retourné dans .env à NOTION_DAILY_REPORT_PAGE_ID
```

Tu verras les 2 sous-pages apparaître dans Notion sous ta page parente. Elles seront vides au début, et remplies à chaque run du pipeline.

## 8. Test local

Teste sur 1 seule news pour valider (~3 min, ~0,25 €) :

```bash
python test_pipeline.py 1
```

Tu dois voir :
```
Collecte : ~15-25 news brutes
Sélection top 1 : [...]
Enrichissement 1/1 : ...
Génération image 1/1 : ...
Image sauvegardée : data/images/20260424_01_infographie.png
```

Ouvre l'image générée :

```bash
open data/images/20260424_01_infographie.png    # macOS
xdg-open data/images/20260424_01_infographie.png # Linux
```

Tu dois voir une infographie style magazine cyan. Si oui, tout fonctionne.

**Optionnel** — tester le carrousel (5 min, ~0,50 €) :

```bash
python test_carousel.py
```

Vérifie qu'une page "Carrousel du JJ/MM" apparaît dans ta database Notion avec les slides attachées.

## 9. Déploiement Railway

### 8.1 Se connecter

```bash
railway login
```

(Ouvre un navigateur, connecte-toi avec ton compte Railway.)

### 8.2 Créer le projet

```bash
railway init --name veille-ia
```

Choisis ton workspace personnel.

### 8.3 Créer un service

```bash
railway add --service veille-ia
```

Sélectionne "Empty Service" quand demandé, nom : `veille-ia`.

### 8.4 Pousser les variables d'environnement

Copie ce script et lance-le depuis le dossier du projet :

```bash
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  [[ "$key" == "GMAIL_TOKEN_PATH" || "$key" == "GMAIL_CREDENTIALS_PATH" ]] && continue
  [[ "$key" == "REDDIT_CLIENT_ID" && -z "$value" ]] && continue
  [[ "$key" == "REDDIT_CLIENT_SECRET" && -z "$value" ]] && continue
  echo "Set $key"
  railway variables --service veille-ia --set "$key=$value"
done < .env
```

### 8.5 Pousser le code

```bash
railway up --service veille-ia --detach
```

Attends 2-3 min le build. Vérifie le statut :

```bash
railway status --json | python3 -c "import json,sys; d=json.load(sys.stdin); svc=d['environments']['edges'][0]['node']['serviceInstances']['edges'][0]['node']; print('Status:', svc['latestDeployment']['status'])"
```

Doit retourner `SUCCESS`.

### 8.6 Vérifier le cron

Railway lit automatiquement le cron depuis `railway.toml` (`0 4 * * *` = 6h Paris été).

Pour vérifier :

```bash
railway status --json | python3 -c "import json,sys; d=json.load(sys.stdin); svc=d['environments']['edges'][0]['node']['serviceInstances']['edges'][0]['node']; print(svc['latestDeployment']['meta']['serviceManifest']['deploy'])"
```

Tu dois voir `'cronSchedule': '0 4 * * *'` dans la sortie.

## 10. Publier l'app Google Cloud en production

**IMPORTANT** : sans cette étape, ton `refresh_token` Gmail expire après 7 jours et le bot casse.

- Aller sur https://console.cloud.google.com/ → ton projet `veille-ia`
- Menu ☰ → **APIs & Services** → **OAuth consent screen** (ou nouvelle UI : Google Auth Platform → Audience)
- Chercher le bouton **Publish app** / **Passer en production**
- Confirm

Pas de review Google nécessaire pour le scope `gmail.readonly`.

## 11. Vérification finale

Le prochain cron Railway se déclenchera à la prochaine échéance (4h UTC = 6h Paris été / 5h hiver).

Pour tester **dès maintenant** :
- Aller sur le dashboard Railway de ton projet
- Dans Deployments, clic sur **...** du dernier → **Redeploy**
- Attendre 25 min
- Vérifier Notion → nouvelles pages avec images

Si tout est bon, rien à faire le lendemain matin — Notion se remplira tout seul.

## Coûts à surveiller

Au bout du 1er mois, vérifie :
- Anthropic Usage → https://console.anthropic.com/settings/usage
- OpenAI Usage → https://platform.openai.com/usage
- Railway → Settings → Usage

Si un service dépasse ton budget, ajuste `MAX_NEWS_PER_DAY` dans `config/settings.py` ou skip le carrousel.

## Besoin d'aide ?

Voir [TROUBLESHOOTING.md](TROUBLESHOOTING.md) pour les erreurs fréquentes.
