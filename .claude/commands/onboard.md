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
7. **Tu utilises les MCPs Notion et Supabase pour toutes les actions sur ces services.** Les MCPs sont un pré-requis annoncé à l'utilisateur (cf. la page Notion client). Si l'utilisateur n'a pas connecté le MCP Notion ou le MCP Supabase, **interromps l'onboarding** et demande-lui de les connecter via `/mcp` avant de continuer. **Tu ne demandes JAMAIS à l'user de faire à la main ce que tu peux faire toi-même via MCP.**
8. **Une seule exception : le SQL Supabase.** L'application des migrations SQL Supabase reste manuelle pour l'utilisateur (étape 7.3 ci-dessous), parce qu'il n'y a pas d'API officielle fiable pour exécuter du DDL via REST. Tu lui dictes le SQL à coller, c'est tout.

## Workflow d'onboarding (10 étapes)

### Étape 0 — Bienvenue + diagnostic initial

Présente-toi brièvement :

> 👋 Salut ! Je vais t'aider à installer ton **système de veille automatisé**, un pipeline qui va générer chaque matin des infographies + un carrousel Instagram à partir de l'actualité de **TON sujet** (IA, marketing, crypto, design, finance, lifestyle... à toi de choisir), et tout publier dans ta base Notion.
>
> Tu vas avoir besoin de créer **3 comptes API** (Anthropic, OpenAI, Google), 1 compte Notion, 1 compte Supabase (gratuit) et 1 compte Railway (~5€/mois). Compte ~30 minutes pour tout configurer la première fois.
>
> Avant de commencer, j'ai 2 questions :
> 1. Tu as déjà un compte sur certains de ces services, ou on part de zéro partout ?
> 2. Tu veux installer en local seulement (pour tester) ou directement déployer sur Railway pour que ça tourne tous les jours en automatique ?

Attends sa réponse, puis adapte le rythme. S'il a déjà des comptes, accélère sur ces étapes.

### Étape 0 bis — Choisir le sujet de la veille (CRITIQUE)

Ce starter est neutre : il fonctionne pour n'importe quelle thématique. Demande à l'utilisateur :

> 🎯 **Sur quel sujet veux-tu faire ta veille automatique ?**
>
> Quelques exemples :
> - "IA" (intelligence artificielle) — défaut, sources pré-configurées
> - "Marketing digital" (HubSpot, Marketing Brew, etc.)
> - "Cryptomonnaies" (CoinDesk, Bankless, etc.)
> - "Design produit / UX"
> - "Finance personnelle / investissement"
> - "Lifestyle / productivité"
> - Ou ton sujet à toi.

Une fois qu'il te répond (ex: "Marketing digital"), tu adaptes tout :

**A) Tu détermines 3 valeurs et tu les notes (à mettre dans `.env` à l'étape 3)** :
- `TOPIC_NAME` : nom court capitalisable (ex: "Marketing", "Crypto", "Design")
- `TOPIC_DESCRIPTION` : phrase pleine pour les prompts (ex: "marketing digital pour indépendants", "actualité crypto", "design produit et UX")
- `BRAND_NAME` : nom de marque visible (ex: "Marketing Daily", "CryptoBrief", "Design Watch", ou simplement "Veille [TOPIC_NAME]")

**B) Tu proposes des sources adaptées** au sujet (à appliquer à l'étape 6 dans `config/settings.py`) :
- Pour les **RSS_FEEDS** : propose 4-8 RSS pertinents pour le sujet. Si l'user dit "marketing", suggère HubSpot Blog, Neil Patel, Marketing Brew, etc. Si "crypto", suggère CoinDesk, The Block, Bankless. Si "IA", garde la liste par défaut. Tu peux faire un `WebSearch` pour confirmer les URLs RSS exactes si tu n'es pas sûr.
- Pour les **SUBREDDITS** : propose 3-5 subreddits actifs sur le sujet (ex: marketing → r/marketing, r/SEO, r/PPC).
- Pour les **NEWSLETTER_SENDERS** : suggère 3-5 newsletters par email avec leurs adresses d'expéditeur exactes (ex: marketing → bensbites→marketing brew, the hustle, etc.). L'user devra s'y abonner avant que ça marche.

**C) Tu adaptes l'AUDIENCE_DESCRIPTION** (variable libre) à la cible. Par défaut elle est générique mais l'idéal est qu'elle décrive précisément l'audience que l'user veut atteindre. Tu peux lui poser la question :

> Pour calibrer le scoring viral, décris-moi l'audience à qui tu veux parler en 2 phrases (ex: "Freelances marketing francophones débutants à intermédiaires, qui galèrent à attirer des clients").

Tu génères ensuite une `AUDIENCE_DESCRIPTION` complète (5-10 lignes) calquée sur la structure existante (audience cible + ce qui les fait réagir + ce qui les ennuie).

**Note technique** : l'utilisateur peut SKIP cette étape et garder les défauts IA si c'est ce qu'il veut. Dans ce cas, ne touche pas à `RSS_FEEDS`, `SUBREDDITS`, `NEWSLETTER_SENDERS` (laisse les valeurs IA par défaut).

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

**Si l'utilisateur a choisi un sujet à l'étape 0 bis**, dicte-lui dès maintenant les 3 lignes à ajouter (ou décommenter) en haut du `.env` :

```
TOPIC_NAME=Marketing
TOPIC_DESCRIPTION=marketing digital
BRAND_NAME=Marketing Daily
```

(Adapte aux valeurs choisies à l'étape 0 bis. S'il a gardé "IA" par défaut, ces 3 lignes peuvent rester commentées — les défauts du code sont déjà sur "IA".)

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

### Étape 6 — Notion (intégration + page parente + database)

L'objectif : avoir une intégration Notion qui peut écrire dans son workspace, et une database avec les 11 propriétés exactes — **créée par toi, pas par l'user**.

**6.1 Créer l'intégration interne (manuel — l'user clique)**

C'est la seule action Notion qui ne peut pas être faite via API. Guide-le :

> 1. Va sur https://www.notion.so/profile/integrations
> 2. "+ New integration" → nom : "Veille Bot" (ou ce que tu veux) → workspace : le tien → type : Internal
> 3. Capabilities : Read content, Update content, Insert content
> 4. Copie le **Internal Integration Secret** (commence par `secret_…` ou `ntn_…`)
> 5. Colle-le dans `.env` à `NOTION_API_KEY=…`

**6.2 Créer la page parente + la partager avec l'intégration (manuel — 30 secondes)**

> 1. Dans ton workspace Notion, crée une **page vide** avec le nom de ton choix (ex : "Veille Marketing", "Crypto Watch"…)
> 2. Sur cette page, clic ⋯ en haut à droite → **Connections** → ajoute ton intégration
> 3. Copie l'ID de la page (32 chars dans l'URL, sans tirets, avant le `?`)
> 4. Colle-le dans `.env` à `NOTION_PARENT_PAGE_ID=…`

**6.3 Créer la database avec les 12 propriétés (auto — TU le fais via MCP Notion)**

À ce stade, tu as `NOTION_API_KEY` + `NOTION_PARENT_PAGE_ID` dans `.env` ET le MCP Notion connecté.

**Tu utilises le MCP Notion** (`mcp__notion__notion-create-database` ou équivalent) pour créer la database sous `NOTION_PARENT_PAGE_ID`. Le contrat précis des 12 propriétés (noms, types, options de Select) est dans **`NOTION_SETUP.md`** — lis-le et applique-le exactement, le pipeline Python s'appuie sur ces noms et types.

Le titre de la database doit être : `Veille {BRAND_NAME}` (ex : `Veille Marketing Daily`).

Une fois créée :

1. Récupère l'ID de la database (32 caractères, sans tirets)
2. Écris-le dans `.env` à `NOTION_DATABASE_ID=…`
3. Demande à l'user de rafraîchir sa page Notion → confirme visuellement que la database "Veille [BRAND_NAME]" est bien apparue avant de continuer

> ⚠️ **Si le MCP Notion n'est pas connecté à la session :** STOP. Demande à l'user de le connecter via `/mcp` (cf. l'étape 3 du guide d'installation client). Sans ça, tu ne peux pas continuer l'onboarding sans demander à l'user de tout faire à la main, ce qui n'est pas le but.

### Étape 6 bis — Adapter les sources au sujet (uniquement si sujet ≠ IA)

Si l'user a choisi un sujet ≠ IA à l'étape 0 bis, modifie **`config/settings.py`** pour mettre les sources adaptées :

- Remplace `RSS_FEEDS` par les RSS pertinents pour son sujet (URLs trouvées via `WebSearch` si nécessaire — vérifie qu'elles renvoient bien du XML valide)
- Remplace `SUBREDDITS` par les subreddits actifs sur le sujet
- Remplace `NEWSLETTER_SENDERS` par les expéditeurs des newsletters auxquelles l'user va s'abonner

**Important** : avant de toucher à `NEWSLETTER_SENDERS`, demande à l'user de :
1. S'inscrire à 3-5 newsletters dans son sujet via son adresse Gmail dédiée
2. Recevoir au moins 1 email de chacune (sinon `NEWSLETTER_SENDERS` ne fera rien remonter)

Si l'user veut garder le défaut IA, **skip cette étape**.

### Étape 7 — Supabase (storage + cache + logs)

**7.1 Créer le projet Supabase (manuel — l'user clique)**

> 1. https://supabase.com → "Start your project" (gratuit)
> 2. New project, région **eu-west-1** (Paris) ou la plus proche
> 3. Attends ~2 min que le projet finisse de provisionner
> 4. Settings → API → copie `URL` + `service_role` key (PAS la anon key)
> 5. Colle dans `.env` à `SUPABASE_URL=` et `SUPABASE_SERVICE_KEY=`

**7.2 Créer le bucket d'images (auto — TU le fais via MCP Supabase)**

Utilise le MCP Supabase pour créer un bucket public nommé `veille-images` dans le projet de l'user.

> 💡 Si l'user a choisi un autre nom de bucket, mets à jour `SUPABASE_BUCKET=…` dans `.env`. Par défaut : `veille-images`.

> ⚠️ **Si le MCP Supabase n'est pas connecté :** STOP, demande à l'user de le connecter via `/mcp`.

**7.3 Appliquer les 2 migrations SQL — étape MANUELLE assumée**

> ⚠️ **Cette étape reste manuelle pour l'utilisateur, c'est la SEULE étape technique manuelle de tout l'onboarding.** Si le MCP Supabase de la session expose un outil d'exécution SQL DDL fiable, utilise-le et skip ce qui suit. Sinon (cas par défaut, beaucoup de MCPs Supabase n'exposent pas le DDL), guide l'user dans le SQL Editor :

> 📋 **Étape manuelle (~1 min)** — tu vas coller 2 SQL dans Supabase :
>
> 1. Ouvre Supabase → **SQL Editor** → **New query**
> 2. Affiche-toi le 1er SQL avec : `cat observability/migrations/001_api_calls.sql`
> 3. Copie-colle son contenu dans le SQL Editor → clique **Run**
> 4. Vérifie : "Success. No rows returned"
> 5. Refais pareil avec le 2e fichier : `observability/migrations/002_daily_runs.sql`
>
> ✅ **Vérification** : dans Supabase → **Table Editor**, tu dois voir 2 nouvelles tables : `api_calls` et `daily_runs`. Si oui, c'est bon, on continue.

Affiche le contenu des 2 fichiers à l'écran pour faciliter le copier-coller :

```bash
cat observability/migrations/001_api_calls.sql
cat observability/migrations/002_daily_runs.sql
```

Attends que l'user te confirme avoir vu les 2 tables apparaître dans le Table Editor avant de continuer.

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
