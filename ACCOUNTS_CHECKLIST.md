# Checklist des comptes à créer

Coche chaque ligne au fur et à mesure. L'ordre proposé est optimal (le plus long en dernier).

## 1. Anthropic (Claude) — 3 min

- [ ] Compte sur https://console.anthropic.com/
- [ ] Ajouter un moyen de paiement (carte) dans Settings → Billing
- [ ] Créer une API key dans Settings → API Keys → Create Key
- [ ] **Activer le web search** dans Settings → Privacy (coche la case "Web Search")
- [ ] Copier la clé → `ANTHROPIC_API_KEY=sk-ant-api03-...`

Budget minimum conseillé : 5 € pour tester.

## 2. OpenAI (gpt-image-2) — 3 min

- [ ] Compte sur https://platform.openai.com/
- [ ] Ajouter un moyen de paiement + pré-recharger le compte (10 € minimum)
- [ ] **Vérifier ton organisation** (Settings → Organization) — requis pour gpt-image-2
- [ ] Créer une API key dans Dashboard → API keys → Create new secret key → "All permissions"
- [ ] Copier la clé → `OPENAI_API_KEY=sk-proj-...`

Si gpt-image-2 n'est pas disponible dans ta liste de modèles accessibles, contacte le support OpenAI ou utilise gpt-image-1 (il faut ajuster `OPENAI_IMAGE_MODEL` dans `config/settings.py`).

## 3. Google AI Studio (Gemini) — 2 min

- [ ] Compte sur https://aistudio.google.com/
- [ ] Get API key → Create API key in new project
- [ ] Copier la clé → `GEMINI_API_KEY=AIza...`

Gemini 3 Pro Image est gratuit jusqu'à une certaine limite (~50 requêtes/min). Pour le carrousel quotidien tu restes largement dans la tranche gratuite au début.

## 4. Notion — 5 min

### Créer l'intégration interne
- [ ] Compte sur https://www.notion.so/ (si pas déjà)
- [ ] Aller sur https://www.notion.so/profile/integrations
- [ ] **+ New integration** → nom : `Veille Bot`, Type : **Internal**, workspace associé : ton workspace
- [ ] Capabilities : **Read content** + **Update content** + **Insert content**
- [ ] Submit → copier l'**Internal Integration Secret** → `NOTION_API_KEY=ntn_...` (ou `secret_...`)

### Créer la page parente
- [ ] Dans ton workspace, crée une **page vide** avec le nom de ton choix (ex : `Veille IA`, `Marketing Daily`, `Crypto Watch`)
- [ ] **Partage cette page avec l'intégration** : clic ⋯ en haut à droite → **Connections** → ajouter **Veille Bot**
- [ ] Récupérer l'ID de la page (32 chars dans l'URL, sans tirets, avant le `?`) → `NOTION_PARENT_PAGE_ID=...`

### La database — créée automatiquement par Claude

Tu n'as **rien à faire de plus**. Pendant `/onboard`, Claude créera la database (12 propriétés exactes) sous ta page parente via le MCP Notion. Spec dans [NOTION_SETUP.md](NOTION_SETUP.md) si tu veux la consulter.

Pré-requis pour que ça marche : avoir le **MCP Notion connecté à Claude Code** (via `/mcp`). Sans lui, `/onboard` t'arrêtera et te demandera de le connecter.

Les 2 IDs des sous-pages (`NOTION_COST_REPORT_PAGE_ID`, `NOTION_DAILY_REPORT_PAGE_ID`) seront générés plus tard automatiquement par les scripts `setup_cost_report_page.py` et `setup_daily_report_page.py` que Claude lance pour toi.

## 5. Supabase — 3 min

- [ ] Compte sur https://supabase.com/
- [ ] **New project** → nom au choix, région proche de toi, mot de passe au choix
- [ ] Attendre ~2 min que le projet soit provisionné
- [ ] Dans **Project Settings → API** :
  - Copier le **Project URL** → `SUPABASE_URL=https://xxxxx.supabase.co`
  - Copier la **service_role key** (PAS la anon key) → `SUPABASE_SERVICE_KEY=eyJ...`

### Le bucket et le SQL — gérés pendant `/onboard`

- **Bucket d'images** : Claude le crée pour toi via le **MCP Supabase** pendant l'onboarding. Tu n'as rien à cliquer dans l'UI Storage.
- **Migrations SQL** (création des tables `api_calls` et `daily_runs`) : c'est la **seule étape technique manuelle** restante. Pendant `/onboard`, Claude affichera le SQL à coller dans ton SQL Editor → tu colles → Run → c'est fini (~1 min).

Pré-requis : avoir le **MCP Supabase connecté à Claude Code** (via `/mcp`). Sans lui, tu devras créer le bucket à la main.

> ⚠️ La `service_role` key a les pleins pouvoirs sur ton projet Supabase. Ne la commit jamais dans git.

## 6. Gmail + Google Cloud — 20 min

### a) Adresse Gmail dédiée

- [ ] Créer une nouvelle adresse Gmail (ex: `veille-tonnom@gmail.com`) ou utiliser une existante
- [ ] T'abonner à 4-8 newsletters de ton sujet. Suggestions :
  - TLDR AI — https://tldr.tech/ai
  - Ben's Bites — https://bensbites.co/
  - The Neuron — https://www.theneurondaily.com/
  - The Rundown AI — https://www.therundown.ai/
  - Superhuman (Zain Kahn) — https://www.joinsuperhuman.ai/
  - AI Tidbits
  - Techpresso
  - AI Valley
- [ ] Laisser passer 1-2 jours pour accumuler quelques mails avant de lancer le bot

### b) Projet Google Cloud

- [ ] Aller sur https://console.cloud.google.com/
- [ ] En haut, créer un **nouveau projet** → nom : `veille-bot`
- [ ] Menu ☰ → **APIs & Services** → **Library** → chercher `Gmail API` → **Enable**

### c) OAuth consent screen

- [ ] Menu ☰ → **APIs & Services** → **OAuth consent screen**
- [ ] **External** → Create
- [ ] **App name** : `Veille Bot`
- [ ] **User support email** : ton email
- [ ] **Developer contact** : ton email → Save
- [ ] **Scopes** → Add → cocher `https://www.googleapis.com/auth/gmail.readonly` → Update → Save
- [ ] **Test users** → Add → ajoute l'adresse Gmail dédiée de l'étape a) → Save

### d) OAuth client ID

- [ ] Menu ☰ → **APIs & Services** → **Credentials**
- [ ] **+ Create Credentials** → **OAuth client ID**
- [ ] Application type : **Desktop app**
- [ ] Name : `veille-desktop` → Create
- [ ] Dans la liste, clic sur l'icône **Download JSON** à droite de ton client
- [ ] Renomme le fichier en `gmail_credentials.json` et place-le dans `config/gmail_credentials.json`

### e) Générer le token OAuth

- [ ] Dans ton terminal (venv activé) : `python setup_gmail.py`
- [ ] Une fenêtre navigateur s'ouvre → connecte-toi avec l'adresse Gmail dédiée
- [ ] Clique **"Continue"** sur l'écran "Google n'a pas validé cette app" (normal en mode Testing)
- [ ] Autorise → le token se sauvegarde dans `config/gmail_token.json` automatiquement

### f) Publier l'app en production (important)

- [ ] Retourner sur https://console.cloud.google.com/ → ton projet `veille-bot`
- [ ] Menu ☰ → **APIs & Services** → **OAuth consent screen** (ou "Google Auth Platform → Audience" dans la nouvelle UI)
- [ ] Bouton **Publish app** → Confirm
- [ ] Pas de review Google nécessaire pour le scope `gmail.readonly`

> Si tu ne publies pas, le refresh_token expire après **7 jours** et ton bot s'arrête.

## 7. Railway (déploiement) — 5 min

- [ ] Compte sur https://railway.com/ (se connecter avec GitHub recommandé)
- [ ] Ajouter un moyen de paiement dans Account Settings → Billing
- [ ] **Plan Hobby** recommandé (~5 $/mois) — le plan gratuit fonctionne aussi si tu es sous le quota
- [ ] Installer Railway CLI : `npm i -g @railway/cli`
- [ ] Se connecter en local : `railway login`

## Récap : toutes les clés à avoir dans `.env`

Une fois la checklist terminée, tu as ceci à remplir dans ton fichier `.env` :

```bash
# Obligatoires
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIza...
NOTION_API_KEY=ntn_...
NOTION_DATABASE_ID=...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_BUCKET=veille-images

# Gmail (fichiers JSON dans config/, pas dans .env)
GMAIL_TOKEN_PATH=./config/gmail_token.json
GMAIL_CREDENTIALS_PATH=./config/gmail_credentials.json

# Reddit (optionnel — laisser vide pour skipper Reddit)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=veille-ia-bot/1.0
```

## Temps total estimé

- Expérimenté (tu as déjà des comptes) : **20 min**
- Débutant complet (tout de zéro) : **1h30-2h**
