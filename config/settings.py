"""Configuration centralisée. Toutes les variables d'env et paramètres globaux."""
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# override=True : les valeurs du .env priment sur celles déjà définies dans le shell.
# Évite les surprises en local (ex : ANTHROPIC_API_KEY="" exportée par Claude Code).
# Sur Railway, il n'y a pas de fichier .env donc seules les variables Railway s'appliquent.
load_dotenv(override=True)

# Chemins
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
SEEN_URLS_FILE = DATA_DIR / "seen_urls.json"

# Timezone Europe/Paris (pour timestamps dans logs et dates Notion).
# Le cron Railway lui tourne en UTC — voir railway.toml pour la conversion.
TZ = ZoneInfo("Europe/Paris")

# === API Keys ===
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # gardé pour rollback éventuel
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
# Page parente (ex: "Veille IA Superproductif") où setup_cost_report_page.py
# crée une sous-page une fois. Utilisé uniquement par le script de setup.
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")
# ID de la sous-page "Coûts API" générée par le setup. Mis à jour à chaque run
# par publish/notion_cost_report.py:update_cost_report_page().
NOTION_COST_REPORT_PAGE_ID = os.getenv("NOTION_COST_REPORT_PAGE_ID", "")
# ID de la sous-page "Rapport quotidien" générée par setup_daily_report_page.py.
# Mise à jour à chaque run par publish/notion_daily_report.py.
NOTION_DAILY_REPORT_PAGE_ID = os.getenv("NOTION_DAILY_REPORT_PAGE_ID", "")

# === Reddit ===
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "veille-ia-bot/1.0")

# === Gmail (newsletters) ===
# Service account JSON ou OAuth token. Voir NOTION_SETUP.md pour la mise en place.
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", str(ROOT_DIR / "config" / "gmail_token.json"))
GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", str(ROOT_DIR / "config" / "gmail_credentials.json"))

# === Modèles ===
CLAUDE_MODEL = "claude-sonnet-4-6"  # Sonnet 4.6 pour scoring + enrichissement web search
OPENAI_IMAGE_MODEL = "gpt-image-2-2026-04-21"  # OpenAI gpt-image-2 (haute qualité, idéal pour infographies texte FR)
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"  # gardé pour rollback éventuel

# === Pipeline ===
MAX_NEWS_PER_DAY = 10  # Plafond d'images générées
MIN_VIRAL_SCORE = 7    # Score minimum sur 10 pour être retenu
LOOKBACK_HOURS = 30    # Fenêtre de scan (un peu plus que 24h pour pas rater)

# === Sources RSS officielles ===
RSS_FEEDS = {
    "Anthropic": "https://www.anthropic.com/rss.xml",
    "OpenAI": "https://openai.com/blog/rss.xml",
    "Google AI": "https://blog.google/technology/ai/rss/",
    "DeepMind": "https://deepmind.google/blog/rss.xml",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "Mistral": "https://mistral.ai/news/rss.xml",
}

# === Subreddits ===
SUBREDDITS = [
    "singularity",
    "LocalLLaMA",
    "OpenAI",
    "ClaudeAI",
    "artificial",
]
SUBREDDIT_MIN_UPVOTES = 200  # Filtre de qualité pour Reddit

# === Newsletters Gmail ===
# Liste des expéditeurs à surveiller dans la boîte Gmail dédiée à la veille
NEWSLETTER_SENDERS = [
    "bensbites@substack.com",                      # Ben's Bites
    "theneuron@newsletter.theneurondaily.com",     # The Neuron
    "superhuman@mail.joinsuperhuman.ai",           # Superhuman (Zain Kahn)
    "aivalley@mail.beehiiv.com",                   # AI Valley
    "theprohuman@mail.beehiiv.com",                # The Prohuman AI
    "techpresso@dupple.com",                       # Techpresso
    "nextoolai@mail.beehiiv.com",                  # Nextool AI
    "drstorm@substack.com",                        # Dr Joerg Storm
]

# === Audience cible (pour le scoring) ===
# Décrit l'audience pour que Claude calibre le scoring viral
AUDIENCE_DESCRIPTION = """
Audience cible : freelances, indépendants, coachs et consultants francophones.
Ils utilisent l'IA au quotidien dans leur business (création de contenu, automatisation,
prospection, productivité). Ils ne sont pas développeurs, mais sont curieux et
veulent rester à la pointe sans se noyer dans la technique.

Ce qui les fait réagir (score viral haut) :
- Nouvelles features qui changent leur quotidien (ex : Claude Code, ChatGPT Memory)
- Annonces de modèles plus performants ou moins chers
- Cas d'usage business concrets et reproductibles
- Drama et déclarations choc des grands acteurs (Sam Altman, Dario Amodei, etc.)
- Comparaisons entre modèles ou outils
- Stats impressionnantes sur l'adoption ou les performances

Ce qui les ennuie (score bas) :
- Papers de recherche ultra-techniques
- Détails d'architecture (transformers, attention, etc.)
- News de niche dev (nouveaux frameworks, libs)
- Annonces corporate sans impact concret
"""
