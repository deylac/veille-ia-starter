# Setup Notion + Gmail + Reddit

## 1. Créer la base Notion

Crée une nouvelle base de données dans ta workspace Notion avec ces propriétés EXACTES (les noms doivent matcher) :

| Nom de propriété | Type | Options |
|---|---|---|
| Titre | Title | (par défaut) |
| Image générée | Files & media | |
| Source | Select | (auto-rempli au fur et à mesure) |
| URL source | URL | |
| Score viral | Number | Format : Number |
| Format utilisé | Select | annonce, stat, citation, versus |
| Hook suggéré FR | Text | |
| Angle éditorial | Text | |
| Statut | Select | À valider, Validé, Rejeté, Publié |
| Freelance assigné | Person | |
| Date scan | Date | |

### Récupérer le Database ID

1. Ouvre la database en pleine page
2. Copie l'URL : `https://www.notion.so/workspace/<DATABASE_ID>?v=...`
3. Le `DATABASE_ID` est la chaîne de 32 caractères avant le `?`

### Créer l'intégration Notion

1. Va sur https://www.notion.so/profile/integrations
2. Clique "New integration"
3. Nomme-la "Veille Bot"
4. Type : "Internal"
5. Capabilities nécessaires : Read content, Update content, Insert content
6. Copie la "Internal Integration Secret" (commence par `secret_`)
7. Retourne sur ta database, clique les `...` en haut à droite → "Connections" → ajoute "Veille Bot"

## 2. Créer le bucket Supabase

1. Crée un nouveau projet Supabase (ou utilise un existant)
2. Storage → New bucket → nom : `veille-images` → **Public** : ON
3. Settings → API → copie l'URL et la `service_role` key (PAS la anon key)

## 3. Configurer Reddit

1. Va sur https://www.reddit.com/prefs/apps
2. "Create another app" → type : `script`
3. Name : `veille-ia-bot`, redirect URI : `http://localhost`
4. Copie le `client_id` (sous le nom de l'app) et le `client_secret`

## 4. Configurer Gmail (newsletters)

C'est la partie la plus longue à setup, mais ça vaut le coup.

### Créer l'adresse Gmail dédiée
Crée une adresse `veille-tonnom@gmail.com` (ou utilise une existante dédiée).
Abonne-la à : TLDR AI, Ben's Bites, The Rundown AI, AI Tidbits.

### Activer l'API Gmail
1. Va sur https://console.cloud.google.com/
2. Crée un nouveau projet "[Ma Veille]"
3. APIs & Services → Library → cherche "Gmail API" → Enable
4. APIs & Services → OAuth consent screen :
   - User type : External
   - App name : Veille Bot
   - Scopes : ajoute `https://www.googleapis.com/auth/gmail.readonly`
   - Test users : ajoute l'adresse Gmail dédiée
5. APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Type : Desktop app
   - Téléchargé le JSON → renomme-le `gmail_credentials.json` → place-le dans `config/`

### Générer le token initial (à faire une seule fois en local)
Crée un script `setup_gmail.py` à la racine et lance-le :

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
flow = InstalledAppFlow.from_client_secrets_file("config/gmail_credentials.json", SCOPES)
creds = flow.run_local_server(port=0)
with open("config/gmail_token.json", "w") as f:
    f.write(creds.to_json())
print("Token généré dans config/gmail_token.json")
```

```bash
python setup_gmail.py
```

Une fenêtre browser s'ouvre, connecte-toi avec l'adresse Gmail dédiée, autorise l'accès. Le token est sauvegardé dans `config/gmail_token.json`.

### Pour Railway

Tu ne peux pas faire d'OAuth interactif sur Railway. Solution : génère le token en local (étape ci-dessus), puis :
- Soit tu commit le `gmail_token.json` dans le repo (NE PAS faire si repo public)
- Soit tu encodes le contenu du JSON en base64 et tu le passes en variable d'env `GMAIL_TOKEN_B64`, puis tu adaptes `sources/newsletters.py` pour le décoder au démarrage.

Le plus simple si le repo est privé : commit `gmail_token.json`. Le refresh token contenu dedans permet de regénérer l'access token automatiquement.

## 5. Tester en local

```bash
pip install -r requirements.txt
cp .env.example .env
# Édite .env avec tes vraies clés
python main.py
```

Vérifie que les pages apparaissent bien dans ta database Notion avec les images attachées.
