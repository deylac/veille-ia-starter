# Troubleshooting — Erreurs fréquentes

## Erreurs d'installation locale

### `ModuleNotFoundError: No module named 'X'`
L'environnement virtuel n'est pas activé ou les dépendances ne sont pas installées.
```bash
source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

### `Could not resolve authentication method` (Anthropic)
La variable `ANTHROPIC_API_KEY` du shell écrase celle du `.env`. Solution : `config/settings.py` utilise `load_dotenv(override=True)` qui règle le souci. Si ça persiste, dans ton shell :
```bash
unset ANTHROPIC_API_KEY
```

### `from google import genai` échoue
Le virtualenv n'est pas actif, ou le package `google-genai` n'est pas installé. Utilise le binaire Python du venv directement :
```bash
.venv/bin/python main.py
```

## Erreurs Notion

### `'properties'` ne retourne rien ou erreur
Notion utilise depuis 2025 le modèle `data_sources`. La réponse de `databases.retrieve` ne contient plus les propriétés directement — elles sont dans une data_source liée.

Pour créer/modifier des propriétés, utilise l'API REST :
```
PATCH https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}
Notion-Version: 2025-09-03
```

Le code actuel de `publish/notion_push.py` utilise `notion.pages.create(parent={"database_id": ...})` qui reste rétrocompatible.

### `Cannot update color of select with name: X`
Tu essayes de modifier la couleur d'une option existante. L'API Notion refuse. Pour ajouter une option, récupère d'abord les options existantes, ajoute la nouvelle à la liste, puis PATCH.

### La page Notion ne se crée pas (`unauthorized`)
L'intégration Notion n'est pas partagée avec la database. Ouvre la database → `...` en haut à droite → **Connections** → ajoute ton intégration.

## Erreurs Gmail / OAuth

### `Token Gmail introuvable`
Le fichier `config/gmail_token.json` n'existe pas. Lance :
```bash
python setup_gmail.py
```

### `Token has been expired or revoked`
Le `refresh_token` a expiré. Deux causes :
1. **App en mode Testing depuis +7 jours** → publie l'app en "In Production" (section 9 de INSTALL.md)
2. **Token révoqué par l'utilisateur** → relance `python setup_gmail.py` pour en générer un nouveau

### `Access denied` au moment de l'OAuth
Ton email Gmail n'est pas dans les "Test users" du projet Google Cloud. Ajoute-le dans OAuth consent screen → Audience → Test users.

### 0 newsletter récupérée alors que la boîte Gmail en contient
Les expéditeurs configurés dans `NEWSLETTER_SENDERS` (dans `config/settings.py`) ne correspondent pas à ce qui est dans ta boîte. Scan ta boîte et adapte la liste (voir INSTALL.md section 6).

## Erreurs OpenAI

### `Model gpt-image-2-2026-04-21 not found`
Le modèle n'est pas disponible sur ton compte. Vérifie les modèles disponibles :
```python
from openai import OpenAI
client = OpenAI()
for m in client.models.list():
    if 'gpt-image' in m.id: print(m.id)
```
Si tu vois `gpt-image-1` mais pas `gpt-image-2`, édite `config/settings.py` :
```python
OPENAI_IMAGE_MODEL = "gpt-image-1"
```

### Image avec bordure blanche au lieu de crème
gpt-image-2 ajoute parfois des marges blanches pures. Le code a un crop automatique (`_crop_white_borders` dans `generation/openai_image.py`) avec un seuil à 242. Si ça ne suffit pas, baisse le seuil à 240 ou 238.

### Accents français manquants dans les images
Deux causes possibles :
1. **Claude a retiré les accents dans le JSON structuré** → vérifie `pipeline/content_enrichment.py`, la règle "GARDE TOUS LES ACCENTS FRANÇAIS" doit être explicite
2. **gpt-image-2 a mal rendu le texte** → c'est une limite du modèle, rien à faire côté prompt

## Erreurs Supabase

### `Object not found` au download du cache `seen_urls.json`
Normal au premier run — le cache n'existe pas encore. Le code fallback sur cache local puis uploade le premier cache à la fin.

### `Permission denied` à l'upload
Le bucket n'est pas public, ou tu utilises la `anon` key au lieu de la `service_role` key. Vérifie `SUPABASE_SERVICE_KEY` dans `.env`.

### Les images dans Notion sont inaccessibles (lien mort)
Le bucket n'est pas public. Dans Supabase Storage → sélectionne le bucket → Settings → toggle "Public bucket" ON.

### Pas de page "Rapport quotidien" mise à jour dans Notion / pas de coût qui s'affiche
Cause probable : la table `daily_runs` ou `api_calls` n'existe pas. Va dans Supabase → SQL Editor et applique les 2 migrations :
- `observability/migrations/001_api_calls.sql`
- `observability/migrations/002_daily_runs.sql`

Vérifie ensuite dans Table Editor que les 2 tables apparaissent. Le prochain run devrait remplir et publier dans Notion.

### Le script `setup_cost_report_page.py` ou `setup_daily_report_page.py` échoue
- Vérifie `NOTION_PARENT_PAGE_ID` dans `.env` (32 chars sans tirets, copié depuis l'URL de ta page parente)
- Vérifie que ton intégration Notion est partagée sur cette page parente : ⋯ → Connections → Veille IA Bot
- Si l'erreur persiste, recopie l'ID en enlevant tout caractère parasite

### Les pages "Coûts API" ou "Rapport quotidien" existent mais ne se mettent plus à jour
Vérifie que `NOTION_COST_REPORT_PAGE_ID` et `NOTION_DAILY_REPORT_PAGE_ID` dans `.env` correspondent bien aux IDs des sous-pages créées (et pas à la page parente). Si tu as supprimé une sous-page Notion, relance `python setup_cost_report_page.py` (ou `setup_daily_report_page.py`) pour en recréer une et coller le nouvel ID.

## Erreurs Railway

### `Unauthorized. Please run railway login again`
Ta session CLI a expiré. Relance `railway login` dans ton terminal (pas dans un script automatisé).

### Le cron ne se déclenche pas
Vérifie que `cronSchedule` est bien lu depuis `railway.toml` :
```bash
railway status --json | python3 -c "import json,sys; d=json.load(sys.stdin); svc=d['environments']['edges'][0]['node']['serviceInstances']['edges'][0]['node']; print(svc['latestDeployment']['meta']['serviceManifest']['deploy'])"
```
Tu dois voir `'cronSchedule': '0 4 * * *'`.

Si pas, vérifie que `railway.toml` est bien à la racine du projet et que `cronSchedule` est sous la section `[deploy]`.

### Le container tourne mais plante immédiatement
Regarde les logs :
```bash
railway logs -s veille-ia --lines 200 -d
```
Cherche la stacktrace. Causes fréquentes :
- Variable d'env manquante → vérifie `railway variables -s veille-ia`
- `gmail_token.json` pas committé → vérifie `.gitignore` (ne doit PAS exclure `config/gmail_token.json` pour un repo privé)

### Le déploiement ne redéploie pas après push GitHub
Railway n'est pas encore lié au repo GitHub (on a utilisé `railway up` local). Pour connecter GitHub :
- Dashboard Railway → service `veille-ia` → Settings → Source → Connect Repo
- Sélectionne `ton-user/veille-ia` → Main branch

## Erreurs de fond

### Le bot ne trouve pas de news qualifiées (viral_score < 7)
- Tu n'as pas encore reçu de newsletters IA dans ta boîte Gmail → attends 24-48h
- Ou ajuste `MIN_VIRAL_SCORE = 6` dans `config/settings.py` pour être moins sélectif

### Le cache de dedup filtre tout
Les URLs des news d'hier sont encore dans le cache 7 jours. Si tu veux forcer :
```python
# Dans un shell Python (.venv actif)
import os; from dotenv import load_dotenv; load_dotenv('.env', override=True)
from supabase import create_client
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
sb.storage.from_(os.getenv('SUPABASE_BUCKET')).remove(['seen_urls.json'])
```

### Coût mensuel plus élevé que prévu
Vérifie les dashboards de chaque service :
- https://console.anthropic.com/settings/usage
- https://platform.openai.com/usage
- https://railway.com → ton projet → Usage

Leviers pour réduire :
- Baisser `MAX_NEWS_PER_DAY` de 10 à 5 → diminue de ~50% les coûts OpenAI
- Désactiver le carrousel → commenter la Phase 7 dans `main.py`
- Utiliser `gpt-image-1` au lieu de `gpt-image-2` → ~3× moins cher

## En dernier recours

Ouvre Claude Code dans le dossier du projet et copie cette question :

> Diagnostic : j'ai lancé [commande] et j'ai cette erreur [erreur]. Analyse le code, les logs Railway, mes fichiers de config, et dis-moi ce qui ne va pas.

Claude Code a accès à tout et diagnostique vite.
