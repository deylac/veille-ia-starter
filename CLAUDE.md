# Veille (sujet configurable) — Architecture & navigation

> Ce document est lu automatiquement par Claude Code à l'ouverture du repo.
> Il est conçu pour qu'un LLM (ou un nouvel humain) comprenne l'app en 5 minutes
> et sache exactement où chercher pour modifier quoi.

## ⚡ Pour Claude Code — détection d'une 1re installation

Avant toute autre action dans ce repo, vérifie si l'utilisateur vient de cloner
ce starter (= onboarding nécessaire) :

1. Si **`.env` n'existe pas** OU si l'utilisateur dit explicitement quelque chose
   comme « j'ai cloné le repo », « comment installer », « setup », « démarre
   l'onboarding », « help me install » → **propose immédiatement** :

   > 👋 Tu viens de cloner ce starter de veille automatisée. Veux-tu que je te guide pas à pas
   > pour tout configurer ? (~30 minutes la première fois)
   > Lance `/onboard` ou réponds "oui" et je commence.

2. Si l'utilisateur valide → exécute le slash command **`/onboard`** qui contient
   le workflow complet d'installation interactive (10 étapes : Python, API keys,
   Notion, Supabase, sous-pages, premier run, déploiement Railway).

3. Si `.env` existe déjà et que l'utilisateur pose une question fonctionnelle
   (modifier un prompt, ajouter une source, debugger un run), **ne lance PAS**
   l'onboarding — réponds normalement avec la cartographie ci-dessous.

Le slash command `/onboard` se trouve dans `.claude/commands/onboard.md`.
Documentation complémentaire : `INSTALL.md`, `ACCOUNTS_CHECKLIST.md`,
`SETUP_WITH_CLAUDE.md`, `TROUBLESHOOTING.md`, `NOTION_SETUP.md`, `DEPLOY.md`.

---

## 1. Vue d'ensemble

Pipeline Python quotidien qui transforme l'actualité d'un sujet **(configurable via `TOPIC_NAME`)** en infographies + carrousels publiés sur Notion. Sujet par défaut : IA. Mais tu peux mettre Marketing, Crypto, Design, Finance, Lifestyle, etc.

- **Sujet** : variable `TOPIC_NAME` dans `.env` (ou défaut "IA"). Voir aussi `TOPIC_DESCRIPTION` et `BRAND_NAME`.
- **Audience** : freelances, coachs, consultants francophones (cf. `AUDIENCE_DESCRIPTION` dans `config/settings.py`, **personnalisable** par sujet)
- **Déclencheur** : cron Railway tous les jours à 04h UTC (= 06h Paris été, 05h Paris hiver)
- **Sortie** : 3 à 6 infographies + 1 carrousel Instagram poussés en base Notion
- **Stack** : Python 3.11, Anthropic SDK, OpenAI SDK, google-genai, supabase-py, notion-client
- **Hébergement** : Railway (cf. `railway.toml`)
- **Persistence** : Supabase (storage images + cache d'URL + logs API), Notion (publication finale)

## 2. Schéma de flux (orchestration `main.py`)

```
                    Cron Railway 04h UTC
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│ Phase 1 — Collecte multi-sources                                   │
│   sources/rss_official.py  →  Anthropic, OpenAI, Google AI, ...    │
│   sources/reddit.py        →  r/singularity, r/LocalLLaMA, ...     │
│   sources/newsletters.py   →  Gmail (Ben's Bites, Neuron, ...)     │
│   → List[NewsItem] (titre + URL + résumé brut)                     │
├────────────────────────────────────────────────────────────────────┤
│ Phase 2 — Déduplication                                            │
│   pipeline/deduplicate.py  →  hash URL + similarité titres         │
│   Cache 7 jours dans Supabase Storage (seen_urls.json)             │
├────────────────────────────────────────────────────────────────────┤
│ Phase 3 — Scoring viral (Claude Sonnet 4.6)                        │
│   pipeline/score_viral.py  →  score 1-10 par news                  │
│   Filtre MIN_VIRAL_SCORE=7, plafond MAX_NEWS_PER_DAY=10            │
├────────────────────────────────────────────────────────────────────┤
│ Phase 3.5 — Direction éditoriale (Claude Sonnet 4.6)               │
│   pipeline/editorial_director.py  →  cluster, fusion, angles       │
│   Sortie : 3 à 6 items finaux, chacun avec un angle type           │
├────────────────────────────────────────────────────────────────────┤
│ Phase 4 — Enrichissement contenu (Claude Sonnet 4.6 + web_search)  │
│   pipeline/content_enrichment.py  →  JSON structuré 6 blocs        │
│   2-3 recherches web par news pour chiffres et citations           │
├────────────────────────────────────────────────────────────────────┤
│ Phase 5 — Génération infographies (OpenAI gpt-image-2)             │
│   generation/openai_image.py  →  PNG 1024x1536 magazine cyan       │
├────────────────────────────────────────────────────────────────────┤
│ Phase 6 — Publication infographies Notion                          │
│   publish/notion_push.py  →  upload Supabase + page Notion         │
├────────────────────────────────────────────────────────────────────┤
│ Phase 7 — Carrousel Instagram (Gemini 3 Pro Image)                 │
│   pipeline/carousel_builder.py + generation/gemini_carousel.py     │
│   N slides 1080x1350 (cover + slides + outro), publiés en Notion   │
├────────────────────────────────────────────────────────────────────┤
│ Phase 8 — Mark as seen (anti-doublon J+1)                          │
│   pipeline/deduplicate.py:mark_as_seen()                           │
└────────────────────────────────────────────────────────────────────┘
```

Modèle de données pivot transporté entre toutes les phases : `NewsItem`
(défini dans `config/models.py`).

## 3. Structure des dossiers

| Dossier | Responsabilité | Fichiers clés |
|---|---|---|
| `config/` | Settings, modèles, secrets | `settings.py`, `models.py` |
| `sources/` | Collecte des news | `rss_official.py`, `reddit.py`, `newsletters.py` |
| `pipeline/` | Traitement éditorial (scoring, dédup, enrichissement) | `score_viral.py`, `deduplicate.py`, `editorial_director.py`, `content_enrichment.py`, `format_selector.py`, `carousel_builder.py` |
| `generation/` | Génération visuels (LLM image) | `openai_image.py` (principal), `gemini_carousel.py`, `gemini_image.py` (fallback) |
| `publish/` | Publication finale | `notion_push.py` |
| `observability/` | Logging structuré API LLM | `api_logger.py`, `migrations/001_api_calls.sql`, `migrations/002_daily_runs.sql` |
| `data/` | Cache + outputs locaux | `seen_urls.json`, `images/`, `carousels/`, `api_calls.jsonl` |

## 4. Modèle pivot : `NewsItem` (`config/models.py`)

Champs principaux et qui les remplit / les lit :

| Champ | Rempli par | Lu par |
|---|---|---|
| `title`, `url`, `source`, `summary`, `published_at` | sources/* | tout le pipeline |
| `viral_score`, `viral_reason` | `score_viral.py` | `editorial_director.py` (info) |
| `editorial_angle`, `hook_fr` | `score_viral.py` | `content_enrichment.py` |
| `editorial_angle_type`, `editorial_brief` | `editorial_director.py` | `content_enrichment.py` |
| `merged_from_urls` | `editorial_director.py` | `notion_push.py` (sources) |
| `structured_content` (dict JSON 6 blocs) | `content_enrichment.py` | `openai_image.py` (rendu) |
| `web_sources` | `content_enrichment.py` | `notion_push.py` |
| `image_prompt`, `image_path` | `openai_image.py` | `notion_push.py` |
| `visual_format` | hardcodé "infographie" (legacy: `format_selector.py`) | `notion_push.py` |

## 5. Point d'entrée

`main.py:32` — fonction `run()` orchestre les 8 phases avec early-exit si une
phase ne renvoie rien. Erreur fatale -> sys.exit(1). La phase 7 (carrousel) est
non bloquante (try/except qui log mais continue).

## 6. Configuration & secrets

Toutes les variables sont consommées via `config/settings.py`, qui charge `.env`
au démarrage avec `load_dotenv(override=True)`.

| Variable | Usage | Si absente |
|---|---|---|
| `TOPIC_NAME` | Nom court du sujet (ex: "IA", "Marketing"). Défaut : "IA" | défaut "IA" |
| `TOPIC_DESCRIPTION` | Phrase pleine pour les prompts (ex: "marketing digital"). Défaut : "intelligence artificielle" | défaut "intelligence artificielle" |
| `BRAND_NAME` | Marque visible (footer images, titre des sous-pages Notion). Défaut : "Veille {TOPIC_NAME}" | défaut "Veille IA" |
| `AUDIENCE_DESCRIPTION` | Multi-ligne, calibre le scoring viral pour ton audience. Si vide, fallback générique | fallback générique |
| `ANTHROPIC_API_KEY` | Claude Sonnet 4.6 (scoring, éditorial, enrichissement) | crash hard |
| `OPENAI_API_KEY` | gpt-image-2 (génération infographies) | crash hard |
| `GEMINI_API_KEY` | Gemini 3 Pro Image (carrousel + fallback infographie) | crash hard sur phase 7 |
| `NOTION_API_KEY` + `NOTION_DATABASE_ID` | Publication finale | crash phase 6 |
| `NOTION_PARENT_PAGE_ID` | Page parente où setup_*_report_page.py crée les sous-pages | scripts setup ne marchent pas |
| `NOTION_COST_REPORT_PAGE_ID` | Sous-page "Coûts API", MAJ à chaque run | rapport coûts non publié (silencieux) |
| `NOTION_DAILY_REPORT_PAGE_ID` | Sous-page "Rapport quotidien", MAJ à chaque run | rapport quotidien non publié (silencieux) |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` + `REDDIT_USER_AGENT` | Source Reddit | source Reddit désactivée |
| `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` + `SUPABASE_BUCKET` | Storage images + cache URL + logs API | fallback fichiers locaux |
| `GMAIL_TOKEN_PATH` + `GMAIL_CREDENTIALS_PATH` | Source newsletters Gmail | source Gmail désactivée |

Modèles versionnés en dur dans `config/settings.py:41-43` :
- `CLAUDE_MODEL = "claude-sonnet-4-6"`
- `OPENAI_IMAGE_MODEL = "gpt-image-2-2026-04-21"`
- `GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"`

## 7. Conventions

- **Logger par module** : `logger = logging.getLogger(__name__)` en haut de
  chaque fichier. Niveau INFO par défaut, DEBUG pour les détails noisy.
- **Gestion d'erreur** : try/except autour de CHAQUE appel externe (LLM, Notion,
  Supabase). Philosophie : *le pipeline doit toujours produire quelque chose*,
  donc fallback minimal ou skip d'item plutôt que crash global.
- **Logging API** : tout appel LLM passe par `observability.api_logger.log_api_call(...)`
  pour tracer modèle / tokens / coût / succès. Best-effort, ne crashe jamais le pipeline.
- **Modèles LLM versionnés** dans `config/settings.py` (jamais en dur dans les
  modules — ne pas dupliquer).
- **JSON parsing** : Claude renvoie parfois du markdown autour du JSON. Pattern
  systématique : strip ```json ... ``` (cf. `score_viral.py:88`, `editorial_director.py:135`).
- **Troncatures défensives** : tous les champs de `NewsItem` qui finissent dans
  l'image ou Notion sont tronqués à des limites strictes (`_validate_structured`
  dans `content_enrichment.py:230`) — voir aussi point 8.

## 8. Points d'attention pour modifications futures

- **Prompt enrichissement** (`content_enrichment.py:33` `ENRICHMENT_PROMPT`) :
  toute modif des limites de longueur (puces, titres) doit être répliquée dans
  `_validate_structured` (filet de sécurité). Les limites visuelles de
  `gpt-image-2` sont étroites : ne JAMAIS revenir au-delà de 48 chars / puce
  sans validation visuelle (sinon mots tronqués dans le rendu).
- **Template image** (`openai_image.py:30` `PROMPT_TEMPLATE`) : `gpt-image-2` est
  sensible. Tester visuellement 2-3 outputs après toute modif (un changement
  subtil peut casser la grille, la palette, ou la cohérence typo).
- **Schéma `structured_content`** : partagé entre `content_enrichment.py` (writer)
  et `openai_image.py` (reader, via `_build_prompt` et `_format_blocs`). Toute
  évolution du schéma doit toucher les 2 fichiers ensemble.
- **Cron Railway** (`railway.toml`) : exprimé en UTC. 04:00 UTC = 06:00 Paris été
  / 05:00 Paris hiver. Décalage d'1h en hiver accepté.
- **Coût API** : `claude-sonnet-4-6` est le plus cher en cumulé (4 appels par run).
  Si budget serré, le plus simple est de baisser `MAX_NEWS_PER_DAY` ou la
  fréquence du cron, avant de toucher au modèle.
- **Logging API : table de prix** dans `observability/api_logger.py:21`
  (`PRICING`). À mettre à jour quand les fournisseurs changent leurs tarifs.

## 9. Comment lancer / tester / déployer

```bash
# Local — pipeline complet (besoin du .env complet + Supabase + Notion)
python main.py

# Tests partiels
python test_pipeline.py    # pipeline sans publication Notion
python test_carousel.py    # carrousel Gemini uniquement

# Reporting consommation API
python report_api_usage.py                  # 7 derniers jours, vue date+modèle
python report_api_usage.py --days 30        # 30 derniers jours
python report_api_usage.py --by model       # agrégat par modèle
python report_api_usage.py --by step        # agrégat par étape pipeline

# Déploiement
git push origin main   # Railway redéploie auto, le cron toml gère 04:00 UTC
```

## 10. Setup initial

- **Notion** : `NOTION_SETUP.md` (création base, intégration, propriétés)
- **Supabase** : créer un bucket public `veille-images`, puis appliquer dans
  le SQL editor :
  - `observability/migrations/001_api_calls.sql` (logs API)
  - `observability/migrations/002_daily_runs.sql` (rapports quotidiens)
- **Sous-pages Notion (1 fois)** : `python setup_cost_report_page.py` et
  `python setup_daily_report_page.py` créent les sous-pages "Coûts API" et
  "Rapport quotidien" sous `NOTION_PARENT_PAGE_ID`. Coller les IDs retournés
  dans `.env` (et Railway).
- **Gmail (optionnel)** : `setup_gmail.py` pour générer le token OAuth
- **Railway** : `DEPLOY.md`

## Maintenance de ce document

⚠️ **Règle stricte** : ce fichier est la source de vérité de l'architecture.
À mettre à jour dans la même PR que toute modification qui change :
- l'ordre des phases dans `main.py`
- les responsabilités d'un dossier
- les champs principaux de `NewsItem`
- les modèles LLM utilisés
- les variables d'env

Si tu ajoutes un nouveau module, ajoute-le aussi dans la table de la section 3.
