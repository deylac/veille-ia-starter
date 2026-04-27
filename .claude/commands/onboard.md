---
description: Guide l'utilisateur pas à pas pour installer et configurer Veille IA depuis zéro
---

# Onboarding Veille IA

Tu vas guider l'utilisateur dans l'installation complète de Veille IA. Suis ce workflow **dans l'ordre** et **demande confirmation** à chaque étape avant de passer à la suivante. L'objectif : à la fin de l'onboarding, le pipeline doit pouvoir tourner en local et publier sa première infographie + son premier rapport quotidien dans Notion.

## Règles d'or

1. **Pose UNE question à la fois.** N'enchaîne pas plusieurs prompts dans un seul message. Attends la réponse de l'user.
2. **Ne fais jamais de suppositions sur les API keys.** Demande-les explicitement, ne les invente pas.
3. **Vérifie chaque étape avant de continuer.** Ne dis pas "c'est fait" sans avoir prouvé que ça marche.
4. **Si l'user dit "skip" ou "déjà fait" pour une étape**, vérifie quand même que les pré-requis sont en place (ex: vérifier que la clé API est dans `.env`) avant de passer à la suite.
5. **Tone amical et clair.** L'user n'est pas développeur, mais il est curieux. Évite le jargon, donne le "pourquoi" de chaque action.
6. **Utilise les outils Bash/Read/Write/Edit** pour vérifier l'état réel du repo, pas tes suppositions.

## Workflow d'onboarding (10 étapes)

### Étape 0 — Bienvenue + diagnostic initial

Présente-toi brièvement :

> 👋 Salut ! Je vais t'aider à installer Veille IA, un pipeline qui va générer chaque matin des infographies + un carrousel Instagram à partir de l'actualité IA, et tout publier dans ta base Notion.
>
> Tu vas avoir besoin de créer **3 comptes API** (Anthropic, OpenAI, Google), 1 compte Notion, 1 compte Supabase (gratuit) et 1 compte Railway (~5€/mois). Compte ~30 minutes pour tout configurer la première fois.
>
> Avant de commencer, j'ai 2 questions :
> 1. Tu as déjà un compte sur certains de ces services, ou on part de zéro partout ?
> 2. Tu veux installer en local seulement (pour tester) ou directement déployer sur Railway pour que ça tourne tous les jours en automatique ?

Attends sa réponse, puis adapte le rythme. S'il a déjà des comptes, accélère sur ces étapes.

### Étape 1 — Vérifier Python + créer le venv

```bash
python3 --version  # doit afficher 3.11+
```

Si OK, créer le venv :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Vérifie que les dépendances installent bien (au moins `anthropic`, `openai`, `google-genai`, `notion-client`, `supabase`).

### Étape 2 — Créer le `.env` à partir de l'exemple

```bash
cp .env.example .env
```

Demande à l'user : **« Ouvre `.env` dans un éditeur, on va le remplir ensemble étape par étape. »**

### Étape 3 — Anthropic (clé Claude)

Guide l'user :

> 1. Va sur https://console.anthropic.com/settings/keys
> 2. Si tu n'as pas de compte, crée-en un (~30 sec)
> 3. Recharge ton compte avec **5$ minimum** (le pipeline coûte ~$1/jour)
> 4. Clique "Create Key", nomme-la "veille-ia", copie la clé (commence par `sk-ant-api03-…`)
> 5. Colle-la dans ton `.env` à la ligne `ANTHROPIC_API_KEY=…`

Vérifie ensuite avec un test rapide :

```python
.venv/bin/python -c "from anthropic import Anthropic; import os; from dotenv import load_dotenv; load_dotenv(); c = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')); r = c.messages.create(model='claude-sonnet-4-6', max_tokens=10, messages=[{'role':'user','content':'dis OK'}]); print(r.content[0].text)"
```

### Étape 4 — OpenAI (clé gpt-image-2)

> 1. Va sur https://platform.openai.com/api-keys
> 2. Recharge ton compte avec **5$ minimum**
> 3. Crée une clé, copie-la (commence par `sk-…`)
> 4. Colle dans `.env` à `OPENAI_API_KEY=…`

### Étape 5 — Google Gemini (clé pour le carrousel)

> 1. Va sur https://aistudio.google.com/app/apikey
> 2. "Create API key" — pas besoin de carte bancaire pour démarrer (free tier)
> 3. Copie la clé, colle dans `.env` à `GEMINI_API_KEY=…`

### Étape 6 — Notion (intégration + database + page parente)

C'est l'étape la plus longue. Guide pas à pas :

**6.1 Créer l'intégration**
> 1. Va sur https://www.notion.so/profile/integrations
> 2. "+ New integration" → nom : "Veille IA", workspace : le tien
> 3. Copie le **Internal Integration Secret** (commence par `secret_…`)
> 4. Colle dans `.env` à `NOTION_API_KEY=…`

**6.2 Créer la base Notion**

Lis-lui le fichier `NOTION_SETUP.md` et guide-le pour créer la database avec les bonnes propriétés. Une fois faite :
> - Récupère l'ID de la database (32 chars dans l'URL)
> - Colle dans `.env` à `NOTION_DATABASE_ID=…`
> - **Important** : partage la database avec ton intégration "Veille IA" (clic ⋯ en haut à droite → Connections → Veille IA)

**6.3 Récupérer l'ID de la page parente** (pour les sous-pages "Coûts API" + "Rapport quotidien")
> - Crée une page parent "Veille IA" dans ton workspace si tu n'en as pas
> - Partage cette page parent aussi avec l'intégration
> - Copie l'ID de la page (32 chars dans l'URL)
> - Colle dans `.env` à `NOTION_PARENT_PAGE_ID=…`

### Étape 7 — Supabase (storage + cache + logs)

**7.1 Créer le projet Supabase**
> 1. https://supabase.com → "Start your project" (gratuit)
> 2. New project, région **eu-west-1** (Paris) ou la plus proche
> 3. Settings → API → copie `URL` + `service_role` key
> 4. Colle dans `.env` à `SUPABASE_URL=` et `SUPABASE_SERVICE_KEY=`

**7.2 Créer le bucket d'images**
> 1. Storage → New bucket → nom : `veille-ia-images`
> 2. **PUBLIC bucket** (case à cocher) ← essentiel sinon Notion ne peut pas afficher les images

**7.3 Appliquer les 2 migrations SQL**

Affiche le contenu des 2 fichiers de migration :

```bash
cat observability/migrations/001_api_calls.sql
cat observability/migrations/002_daily_runs.sql
```

> Va dans Supabase → SQL Editor → New query → colle le contenu de la 1re migration → Run
> Refais avec la 2e migration.

Vérifie que les 2 tables existent :
> Va dans Supabase → Table Editor → tu dois voir `api_calls` et `daily_runs`

### Étape 8 — Créer les 2 sous-pages Notion (rapports automatiques)

```bash
.venv/bin/python setup_cost_report_page.py
```

Récupère l'ID retourné, colle dans `.env` à `NOTION_COST_REPORT_PAGE_ID=…`

```bash
.venv/bin/python setup_daily_report_page.py
```

Récupère l'ID retourné, colle dans `.env` à `NOTION_DAILY_REPORT_PAGE_ID=…`

### Étape 9 — Premier run de test 🚀

```bash
.venv/bin/python main.py
```

Attends ~5 minutes (le pipeline collecte → score → enrichit → génère 1 image → publie).

Pendant que ça tourne, explique à l'user ce qu'il va voir dans Notion :
- 1 page d'infographie par news retenue
- 1 page de carrousel (3-7 slides Gemini)
- La page "Rapport quotidien" mise à jour avec le détail du run
- La page "Coûts API" mise à jour avec le coût (~$0.30 pour ce run)

Si rien n'a passé le seuil viral aujourd'hui, c'est normal — la page "Rapport quotidien" l'expliquera ("Pipeline OK — ce n'est pas un bug").

### Étape 10 — Déploiement Railway (optionnel mais recommandé)

Lis `DEPLOY.md` et guide l'user pour :
1. Créer un repo GitHub privé avec son code
2. Connecter Railway au repo
3. Copier toutes les vars d'env dans Railway → Variables
4. Configurer le cron (Settings → Cron Schedule : `0 4 * * *` pour 06h Paris été)
5. Vérifier que le 1er déploiement passe

## Fin de l'onboarding

Quand tout est OK :

> 🎉 Ton pipeline Veille IA est opérationnel ! Demain matin à 06h, ton run automatique tournera et tu retrouveras tes nouvelles infographies + carrousel + rapport dans Notion.
>
> Pour modifier le système plus tard (ex: changer le seuil viral, ajouter une source RSS, ajuster le prompt des infographies), tout est documenté dans `CLAUDE.md`. Tu peux me demander n'importe quand : "modifie X dans la config" et je te guiderai.
>
> Tu peux suivre tes coûts en temps réel via :
> - La page Notion **Coûts API** (mise à jour à chaque run)
> - Ou en local : `python report_api_usage.py --days 30 --by model`

## Si l'user bloque ou veut comprendre un point

- Pour les **erreurs** : lis `TROUBLESHOOTING.md`, c'est ta référence
- Pour les **comptes à créer** : lis `ACCOUNTS_CHECKLIST.md`
- Pour comprendre **comment marche le pipeline** : lis `CLAUDE.md` (cartographie complète)
- Pour le **déploiement Railway** : lis `DEPLOY.md`
- Pour la **configuration Notion** : lis `NOTION_SETUP.md`
