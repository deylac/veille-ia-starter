# Déploiement sur Railway

## Étape 1 : Préparer le repo Git

```bash
cd veille-ia
git init
git add .
git commit -m "Initial commit"
# Créer un repo privé sur GitHub puis :
git remote add origin git@github.com:tonpseudo/veille-ia.git
git push -u origin main
```

**Important** : ajoute `.env` et `data/` à `.gitignore` (déjà fait dans le `.gitignore` fourni).

Si tu utilises Gmail : commit `config/gmail_token.json` (le repo doit être PRIVÉ).

## Étape 2 : Créer le projet Railway

1. Va sur https://railway.app/new
2. "Deploy from GitHub repo" → sélectionne `veille-ia`
3. Railway détecte Python automatiquement

## Étape 3 : Configurer les variables d'environnement

Dans Railway → ton projet → Variables, ajoute toutes les variables du `.env.example` :

```
ANTHROPIC_API_KEY
GEMINI_API_KEY
NOTION_API_KEY
NOTION_DATABASE_ID
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
SUPABASE_URL
SUPABASE_SERVICE_KEY
SUPABASE_BUCKET
```

## Étape 4 : Configurer le cron

Railway gère les crons via le concept de "cron schedule" sur un service.

1. Dans ton projet Railway, va dans Settings du service
2. Scroll jusqu'à "Cron Schedule"
3. Mets : `0 6 * * *`
   (Cron en UTC : 6h UTC = 7h Madrid en hiver, 8h en été. Adapte si besoin pour 7h locale stricte.)

Le service tournera ensuite le `python main.py` chaque jour à l'heure prévue, puis s'arrêtera (grâce au `restartPolicyType = "NEVER"` dans `railway.toml`).

## Étape 5 : Tester le déploiement

Avant de laisser tourner le cron, teste manuellement en cliquant "Deploy" dans Railway. Vérifie les logs et la base Notion.

## Coûts Railway

Le service ne tourne que ~5 minutes par jour. Tu seras très en dessous du palier gratuit ou autour de 5€/mois sur le plan Hobby.

## Troubleshooting

- **"Module not found"** : vérifie que `requirements.txt` est à la racine
- **"Notion 401 unauthorized"** : la base n'est pas partagée avec l'intégration
- **"Gemini quota exceeded"** : check ton billing Google AI Studio
- **Pas d'images dans Notion** : vérifie que le bucket Supabase est bien Public
- **Pas de news collectées** : vérifie LOOKBACK_HOURS dans settings.py (peut-être trop court)

## Monitoring

Pour suivre les exécutions, deux options :
1. Logs Railway : tu vois chaque run et ses erreurs
2. Ajouter une notification Slack/Discord à la fin de `main.py` qui envoie un message du type "Veille du 24/04 : 7 images poussées"
