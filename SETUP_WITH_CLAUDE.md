# Phase 2 — Installation avec Claude Code

Ce guide suppose que tu as **déjà terminé la Phase 1** (création des comptes et récupération des clés). Si ce n'est pas fait, va d'abord sur [ACCOUNTS_CHECKLIST.md](ACCOUNTS_CHECKLIST.md).

## Avant de commencer, tu dois avoir sous la main

- **Les 8 clés / valeurs à coller** :
  - `ANTHROPIC_API_KEY` (format `sk-ant-api03-...`)
  - `OPENAI_API_KEY` (format `sk-proj-...`)
  - `GEMINI_API_KEY` (format `AIza...`)
  - `NOTION_API_KEY` (format `ntn_...` ou `secret_...`)
  - `SUPABASE_URL` (format `https://xxxxx.supabase.co`)
  - `SUPABASE_SERVICE_KEY` (format `eyJ...`)
  - `SUPABASE_BUCKET` (ton nom de bucket, ex: `veille-ia-images`)
  - L'ID de la page Notion parent où tu veux créer ta database (récupéré depuis l'URL de la page Notion)

- **Le fichier `gmail_credentials.json`** téléchargé depuis Google Cloud Console, quelque part sur ta machine (probablement dans `~/Downloads/`)

- **Quelques newsletters IA** reçues dans ta boîte Gmail dédiée (au moins 2-3 mails déjà reçus pour que le bot ait de la matière)

- **Claude Code** installé et configuré avec un plan (Pro ou API)

- **Python 3.11+, git, Node.js** sur ta machine (Claude Code te guidera pour installer ce qui manque)

## Étape 1 — Récupérer le code

Ouvre un terminal et clone le repo :

```bash
git clone https://github.com/deylac/veille-ia-starter.git
cd veille-ia-starter
```

Ou si tu as reçu un ZIP, extrais-le et ouvre un terminal dedans :

```bash
cd chemin/vers/veille-ia-starter
```

## Étape 2 — Ouvrir Claude Code

Depuis le dossier du projet :

```bash
claude
```

Claude Code démarre avec accès à tous les fichiers du dossier.

## Étape 3 — Coller le prompt ci-dessous

Copie **tout** le bloc entre les triples backticks (depuis `Tu es` jusqu'à la dernière ligne) et colle-le dans Claude Code.

```
Tu es mon assistant pour déployer le projet "Veille IA" de ce dossier sur ma
machine et sur Railway. J'ai déjà créé tous mes comptes externes et j'ai mes
clés API prêtes à te donner. Tu peux lire README.md, ACCOUNTS_CHECKLIST.md,
INSTALL.md, TROUBLESHOOTING.md et le code source pour tout contexte.

Guide-moi étape par étape. Pour chaque phase :
1. Annonce ce que tu vas faire
2. Lance les commandes toi-même quand c'est toi qui dois agir
3. Quand tu as besoin d'une info de ma part, demande-la clairement et attends
4. Vérifie le résultat avant de passer à la suivante
5. Réponds en français

Suis les phases A à J dans l'ordre. Ne saute jamais d'étape de vérification.

=== PHASE A : prérequis machine ===
Vérifie que j'ai Python 3.11+, pip, git, et Railway CLI (`railway --version`).
Si Railway CLI manque, propose `npm i -g @railway/cli` (vérifie d'abord que j'ai
node/npm). Si gh CLI manque, propose `brew install gh` (ou équivalent selon OS).

=== PHASE B : environnement Python ===
Crée un venv : `python3 -m venv .venv`. Utilise ensuite `.venv/bin/python` et
`.venv/bin/pip` pour toutes les commandes Python (ne compte pas sur `source
.venv/bin/activate` qui ne fonctionne pas bien dans ton Bash).
Installe requirements.txt. Vérifie que les imports passent :
  .venv/bin/python -c "from main import run; print('imports OK')"

=== PHASE C : fichier .env ===
Copie .env.example vers .env. Demande-moi les 7 valeurs une par une, colle-les
dans .env avec Edit (pas Write). Laisse vides les REDDIT_CLIENT_ID et
REDDIT_CLIENT_SECRET (Reddit est optionnel et demande un reCAPTCHA).

Notes importantes pour l'édition de .env :
- Garde les commentaires du template
- Pas d'espaces autour du `=`
- Pas de guillemets autour des valeurs

=== PHASE D : tester les credentials ===
Après avoir rempli .env, teste chaque credential sans lancer le pipeline complet :
1. Anthropic : appelle messages.create avec model=claude-sonnet-4-6, max_tokens=20,
   message="Reply with exactly: OK". Vérifie la réponse.
2. OpenAI : liste les modèles disponibles, vérifie que `gpt-image-2-2026-04-21`
   OU `gpt-image-1` est présent. Si seulement gpt-image-1, dis-le moi et propose
   d'éditer config/settings.py pour utiliser gpt-image-1.
3. Gemini : liste les modèles, vérifie que `gemini-3-pro-image-preview`
   (ou équivalent) est accessible.
4. Notion : appelle GET /v1/users/me pour valider la clé. Demande-moi l'ID de
   la page Notion parent où je veux créer la database (je l'extraie de l'URL de
   la page).
5. Supabase : list_buckets() pour vérifier que le bucket existe et est public.
   Si le bucket n'existe pas, dis-le moi et guide-moi pour le créer manuellement.

Pour tout test, utilise `.venv/bin/python -c "..."` avec override=True dans
load_dotenv (à cause de ANTHROPIC_API_KEY potentiellement définie à vide dans
le shell par Claude Code).

=== PHASE E : créer la database Notion ===
Utilise l'API Notion version 2025-09-03. Fais un POST sur /v1/databases avec
parent={"type":"page_id", "page_id": <ID_PAGE_PARENT>}, title "Veille IA",
is_inline=True, et les 12 propriétés exactes :
  - Titre (title)
  - Image générée (files)
  - Source (select, options vides)
  - URL source (url)
  - Score viral (number, format number)
  - Format utilisé (select : infographie pink, carrousel purple, annonce blue,
    stat green, citation yellow, versus orange)
  - Hook suggéré FR (rich_text)
  - Angle éditorial (rich_text)
  - Statut (select : "À valider" yellow, "Validé" green, "Rejeté" red,
    "Publié" blue)
  - Freelance assigné (people)
  - Date scan (date)
  - Type de document (select : infographie blue, carrousel pink)

Récupère le database_id et colle-le dans .env sous NOTION_DATABASE_ID.

Vérifie ensuite en créant une page de TEST dans cette database (propriétés :
Titre="TEST", Source="TEST", Score viral=10, Format utilisé="infographie",
Type de document="infographie", Statut="À valider"). Si succès, archive la
page de test immédiatement.

=== PHASE F : Gmail OAuth ===
Demande-moi où se trouve mon fichier gmail_credentials.json téléchargé. Copie-le
à config/gmail_credentials.json. Puis lance en background :
  .venv/bin/python setup_gmail.py

Monitor sa sortie en attendant la ligne "Please visit this URL". Dis-moi de
m'authentifier dans la fenêtre qui s'est ouverte. Attends la fin (exit 0).
Vérifie que config/gmail_token.json existe.

Ensuite, scan ma boîte Gmail et identifie les 8-12 derniers expéditeurs de
newsletters IA (ceux qui apparaissent dans les messages récents). Compare avec
la liste NEWSLETTER_SENDERS dans config/settings.py et adapte-la si besoin
pour matcher les expéditeurs que je reçois vraiment. Fais un Edit sur le
fichier pour mettre ma vraie liste.

Teste ensuite : `.venv/bin/python -c "from sources.newsletters import
fetch_newsletter_news; print(len(fetch_newsletter_news()))"`. Tu dois voir un
nombre > 0.

=== PHASE G : test local minimal ===
Lance `.venv/bin/python test_pipeline.py 1` en background. Monitor sa sortie
(grep "Enrichissement|Image sauvegardée|ERROR"). Durée ~3 min. Ne coûte que
~0.25 €. Si succès, ouvre l'image générée avec `open data/images/...`.

Si test OK, passe à la phase suivante. Si ERROR, diagnostique avant de
continuer.

=== PHASE H : créer le repo GitHub privé ===
Vérifie que `gh auth status` est OK. Si pas authentifié, propose-moi
`gh auth login`.

Init le repo local :
  git init -b main
  git add .
  git status  # vérifie que .env n'est PAS staged (il doit être gitignored)
  git commit -m "Initial commit — mon pipeline Veille IA personnel"

Crée le repo GitHub privé :
  gh repo create veille-ia --private --source=. --push

Confirme-moi l'URL du nouveau repo.

=== PHASE I : déploiement Railway ===
Lance `railway login` si je ne suis pas connecté (en interactif, le browser
va s'ouvrir). Une fois connecté, liste mes workspaces : `railway list`.

Crée le projet :
  railway init --name veille-ia --workspace "<MON_WORKSPACE>"

Ajoute un service empty :
  railway add --service veille-ia

(Utilise l'option "Empty Service" quand demandé.)

Pousse toutes les variables d'env depuis .env avec une boucle bash
(skip commentaires, lignes vides, GMAIL_*_PATH, et REDDIT_CLIENT_* vides) :

  while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    [[ "$key" == "GMAIL_TOKEN_PATH" || "$key" == "GMAIL_CREDENTIALS_PATH" ]] && continue
    [[ "$key" == "REDDIT_CLIENT_ID" && -z "$value" ]] && continue
    [[ "$key" == "REDDIT_CLIENT_SECRET" && -z "$value" ]] && continue
    echo "Set $key"
    railway variables --service veille-ia --set "$key=$value"
  done < .env

Déploie : `railway up --service veille-ia --detach`.

Monitor le build avec :
  while true; do
    dep_status=$(railway status --json | python3 -c "import json,sys;
    d=json.load(sys.stdin);
    svc=d['environments']['edges'][0]['node']['serviceInstances']['edges'][0]['node'];
    print(svc['latestDeployment'].get('status'))" 2>/dev/null)
    echo "Railway: $dep_status"
    case "$dep_status" in SUCCESS|CRASHED|FAILED) exit 0;; esac
    sleep 15
  done

Quand c'est SUCCESS, vérifie que le cron est bien détecté depuis railway.toml :
  railway status --json | python3 -c "import json,sys;
  d=json.load(sys.stdin);
  svc=d['environments']['edges'][0]['node']['serviceInstances']['edges'][0]['node'];
  print('cron:', svc['latestDeployment']['meta']['serviceManifest']['deploy'].get('cronSchedule'))"

Doit afficher `cron: 0 4 * * *`.

=== PHASE J : récap final ===
Fais-moi un récap clair avec :
- URL du dashboard Railway de mon projet
- URL de mon repo GitHub privé
- URL de ma database Notion
- Heure du prochain cron (le lendemain à 6h Paris en été, 5h en hiver)
- Les 2 points d'attention :
  1. Publier l'app Google Cloud en "In Production" (sinon refresh_token expire
     après 7 jours)
  2. Regénérer les clés API dans quelques jours par sécurité (surtout si elles
     ont transité par le chat)
- Le coût mensuel estimé (~70 €/mois)
- Comment tester manuellement depuis le dashboard Railway (Deployments → ... →
  Redeploy)

Règles globales :
- Réponds toujours en français
- Vérifie chaque étape avant de passer à la suivante
- Si une commande échoue, diagnostique avant de réessayer
- À la fin de chaque phase, fais un mini récap de ce qui vient d'être fait
- Pour les clés API que je te donne, utilise-les DIRECTEMENT (ne me demande
  pas de les mettre dans .env moi-même, tu le fais avec Edit)

Commence par la Phase A maintenant.
```

## Étape 4 — Laisse Claude Code te guider

Il va te poser des questions au fur et à mesure :
- Valider qu'une commande a réussi
- Te demander une clé API, un ID Notion, le chemin du `gmail_credentials.json`
- Te demander de t'authentifier dans un navigateur (Gmail OAuth, Railway)

Réponds honnêtement. Si quelque chose plante, Claude Code le verra dans ses logs et essaiera de diagnostiquer tout seul — donne-lui juste l'erreur si besoin.

**Durée estimée Phase 2** : 30 min à 1h si tu as tout préparé en Phase 1.

## Étape 5 — Tester que ça marche

Dès la fin de la Phase 2, tu peux déclencher un run manuel depuis le dashboard Railway :

1. Va sur l'URL Railway que Claude Code t'a donnée
2. Ouvre ton service `veille-ia` → onglet **Deployments**
3. Sur le dernier deployment, clique `...` → **Redeploy**
4. Attends ~25 min
5. Ouvre ta database Notion → tu dois voir ~8-10 pages infographies + 1 page carrousel

## Si tu veux faire sans Claude Code

Suis le guide manuel [INSTALL.md](INSTALL.md).

## Après l'installation

1. **Jour 1** : vérifie le 1er run automatique à 6h du matin
2. **Semaine 1** : publie l'app Google Cloud en "In Production" (voir [TROUBLESHOOTING.md](TROUBLESHOOTING.md) si tu ne trouves pas le bouton)
3. **Mois 1** : regarde la facture réelle (Anthropic + OpenAI + Railway) et ajuste `MAX_NEWS_PER_DAY` si besoin

C'est tout. Le bot tourne tout seul, tu vis ta vie, et tes contenus arrivent dans Notion chaque matin.
