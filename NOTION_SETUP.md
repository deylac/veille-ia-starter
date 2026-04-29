# Notion — Spec de la database (référence interne)

> 🤖 **Ce fichier est une référence pour Claude Code.** L'utilisateur n'a pas à lire ni à appliquer ce qui suit manuellement — Claude crée la database tout seul à l'étape 6.3 de `/onboard` via le MCP Notion (qui est un pré-requis annoncé au client).

## Contrat de la database

Nom de la database : `Veille {BRAND_NAME}` (ex : `Veille Marketing Daily`).

Parent : la page Notion dont l'ID est dans `NOTION_PARENT_PAGE_ID` (créée et partagée avec l'intégration par l'utilisateur).

### 12 propriétés exactes

Les noms ET les types DOIVENT correspondre — le pipeline Python s'appuie dessus.

| Nom de propriété | Type | Options / format |
| --- | --- | --- |
| Titre | `title` | (par défaut, propriété principale) |
| Image générée | `files` | — |
| Source | `select` | options vides (auto-remplies au fil des runs) |
| URL source | `url` | — |
| Score viral | `number` | format : `number` |
| Format utilisé | `select` | options : `infographie`, `carrousel`, `annonce`, `stat`, `citation`, `versus` |
| Hook suggéré FR | `rich_text` | — |
| Angle éditorial | `rich_text` | — |
| Statut | `select` | options : `À valider`, `Validé`, `Rejeté`, `Publié` |
| Freelance assigné | `people` | — |
| Date scan | `date` | — |
| Type de document | `select` | options : `infographie`, `carrousel` |

> Spec validée le 2026-04-29 par création de DB test via MCP Notion : tous les types et options ont été acceptés par Notion sans erreur.

## Ce que fait Claude pendant `/onboard` (étape 6)

1. **6.1 — User crée l'intégration interne** sur https://www.notion.so/profile/integrations → copie `secret_…` ou `ntn_…` dans `.env` (`NOTION_API_KEY`)
2. **6.2 — User crée une page vide** dans son workspace Notion + la partage avec l'intégration → copie l'ID dans `.env` (`NOTION_PARENT_PAGE_ID`)
3. **6.3 — Claude crée la database lui-même via MCP Notion** avec les 12 propriétés ci-dessus, sous la page parente, titre `Veille {BRAND_NAME}`. Récupère l'ID de la DB et l'écrit dans `.env` à `NOTION_DATABASE_ID=…`.
4. **Claude lance ensuite** `setup_cost_report_page.py` puis `setup_daily_report_page.py` pour créer les 2 sous-pages (Coûts API + Rapport quotidien) sous la page parente. Ces scripts existants utilisent la clé d'intégration interne (`NOTION_API_KEY`).

## Reddit (optionnel)

Si l'utilisateur veut activer la source Reddit :

1. Va sur https://www.reddit.com/prefs/apps
2. "Create another app" → type : `script`
3. Name : `veille-bot`, redirect URI : `http://localhost`
4. Copie le `client_id` (sous le nom de l'app) et le `client_secret` → `.env` (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`)

## Gmail (optionnel — pour scanner les newsletters)

Cf. `setup_gmail.py` à la racine — utilise un OAuth desktop sur un compte Gmail dédié auquel on s'abonne aux newsletters du sujet.
