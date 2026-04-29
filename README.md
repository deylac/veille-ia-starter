# Veille — Ton pipeline automatique de veille quotidienne (sur n'importe quel sujet)

Chaque matin à 6 h, ton bot récupère les news les plus importantes du jour **sur le sujet de ton choix** (IA, marketing, crypto, design, lifestyle, finance, etc.) et les transforme automatiquement en :

- **Des infographies éditoriales premium** (style magazine print) — une par news
- **Un carrousel Instagram** (cover + slides news + outro) — un par jour

Tout arrive dans ta base Notion, prêt à valider et publier sur LinkedIn / Instagram.

> 🎯 **Pas un produit "veille IA" verrouillé** : ce starter fournit le pipeline et une configuration par défaut sur l'IA, mais Claude Code te demande pendant l'onboarding (`/onboard`) sur quel sujet tu veux faire ta veille, puis adapte les sources, prompts et wording automatiquement.

Tu paies tes propres APIs (~25-45 €/mois pour 1-3 infographies + 1 carrousel par jour). Le code tourne sur TON Railway, avec TES clés. Zéro dépendance, zéro abonnement SaaS à vie.

## Comment ça marche

```
Cron Railway 6 h Paris
        |
        v
  RSS officiels (configurables — par défaut RSS IA, à adapter à ton sujet)
  Newsletters par email (configurables — Gmail API)
  Reddit (subreddits configurables, optionnel)
        |
        v
  Claude Sonnet 4.6 : scoring viral 1-10 (top 10)
        |
        v
  Chef éditorial : cluster thématique + angle différencié (3-6 items finaux)
  angles possibles : analyse_outil, tutoriel, decryptage, impact_business,
                     comparaison, debrief
        |
        v
  Claude + web_search : enrichissement (30+ sources web par news)
  structure des 6 blocs adaptée à l'angle attribué
        |
        +---> OpenAI gpt-image-2 : infographies 1024x1536 style magazine cyan
        |
        +---> Gemini 3 Pro Image : carrousel 1024x1280 (5-10 slides, titres FR)
        |
        v
  Notion : 1 page/infographie + 1 page/carrousel
```

Le **chef éditorial** (ajouté en v2) garantit zéro doublon thématique et des angles variés : si 3 news parlent de "GPT-5.5", il décide soit de les fusionner en une synthèse `debrief`, soit de produire des infographies différentes avec angles radicalement distincts (par ex. `comparaison` avec le concurrent + `analyse_outil` sur le modèle seul + `tutoriel` sur un cas d'usage).

## 🚀 Installation guidée par Claude Code

Ce repo est conçu pour être installé en mode "guidé" par Claude Code — Claude crée la database Notion, le bucket Supabase et configure tout pour toi via les MCPs Notion + Supabase. **Tu n'as RIEN à savoir techniquement.**

### Pré-requis (à faire avant de cloner)

1. Créer 6 comptes : Anthropic, OpenAI, Google AI Studio, Notion, Supabase, GitHub. Suis [ACCOUNTS_CHECKLIST.md](ACCOUNTS_CHECKLIST.md) ou [la page Notion d'install client](https://www.notion.so/35076dcb9c4e81af8efcc564c065b957).
2. Installer Claude Code et un abonnement Claude Pro.
3. **Connecter les MCPs Notion + Supabase à Claude Code** via `/mcp`. Sans eux, l'onboarding ne pourra pas créer la database et le bucket pour toi.

### En 3 étapes

```bash
# 1. Cloner le repo
git clone https://github.com/deylac/veille-ia-starter.git veille-ia
cd veille-ia

# 2. Ouvrir dans Claude Code
claude
```

```
# 3. Dans Claude Code, taper :
/onboard
```

Claude va te guider **pas à pas** sur 10 étapes (~30 min) :
1. Vérification Python 3.11+
2. Création du venv + install des dépendances
3. Création de ta clé API Anthropic (Claude)
4. Création de ta clé API OpenAI (gpt-image-2)
5. Création de ta clé API Google Gemini
6. Setup Notion : tu crées juste l'intégration + une page parente, **Claude crée la database 12 propriétés via MCP Notion**
7. Setup Supabase : tu crées juste le projet, **Claude crée le bucket via MCP Supabase**. Seule étape manuelle : coller 2 SQL dans le SQL Editor (~1 min, Claude affiche le contenu).
8. Création des 2 sous-pages Notion automatiques (Coûts API + Rapport quotidien)
9. **Premier run de test** → ta 1re infographie publiée dans Notion 🎉
10. Déploiement Railway (optionnel) pour le cron quotidien

### Installation manuelle (sans Claude Code)

Si tu préfères tout faire à la main, tout est aussi décrit dans [INSTALL.md](INSTALL.md).

## Documentation

| Fichier | Pour quoi |
|---|---|
| [README.md](README.md) | Vue d'ensemble (ce fichier) |
| [CLAUDE.md](CLAUDE.md) | Cartographie complète de l'app (architecture, modules, conventions) — lu auto par Claude Code |
| [.claude/commands/onboard.md](.claude/commands/onboard.md) | Workflow d'installation guidée — déclenché par `/onboard` |
| [ACCOUNTS_CHECKLIST.md](ACCOUNTS_CHECKLIST.md) | Liste des comptes externes à créer (avec liens directs) |
| [INSTALL.md](INSTALL.md) | Installation manuelle (sans Claude Code) |
| [SETUP_WITH_CLAUDE.md](SETUP_WITH_CLAUDE.md) | Notes complémentaires pour l'installation guidée |
| [NOTION_SETUP.md](NOTION_SETUP.md) | Spec interne (12 propriétés de la database) — utilisée par Claude pendant l'onboarding |
| [DEPLOY.md](DEPLOY.md) | Déploiement Railway + configuration du cron |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | FAQ et résolution des erreurs fréquentes |

## Reporting & monitoring

Une fois installé, le pipeline publie automatiquement à chaque run **2 sous-pages Notion** dans ton espace :

- **🗞️ Rapport quotidien** : aujourd'hui (synthèse + raisons des news retenues/rejetées) + 6 jours d'historique en toggles repliables. Utile pour comprendre pourquoi un jour 0 image n'a été publiée — réponse explicite "ce n'est pas un bug".
- **💰 Coûts API** : coût d'aujourd'hui + cumul 7j + cumul 30j + projection mensuelle. Détail par modèle + par étape du pipeline.

Tu peux aussi consulter en CLI :
```bash
python report_api_usage.py --days 30 --by model
```

## Coûts mensuels estimés (vérifiés sur facturation réelle)

Calé sur facturation réelle observée fin avril 2026, pour un volume modéré (1-3 infographies/jour) :

- Anthropic API (scoring + éditorial + enrichissement Claude + web_search) : ~5-15 €
- OpenAI (gpt-image-2 — infographies) : ~5-15 €
- Gemini (carrousel Instagram, ~5-7 slides/jour) : ~3-10 €
- Railway (hébergement cron) : ~5 €
- Supabase (storage + tables, free tier suffit) : 0 €
- Notion : 0 €
- **Total : ~20-45 € / mois** (vérifie ta facture après 1 semaine de prod via la page Notion "Coûts API")

Pour réduire :
- Baisser `MAX_NEWS_PER_DAY` dans `config/settings.py`
- Désactiver le carrousel (commenter la phase 7 de `main.py`) → -5 à -10 €/mois
- Augmenter `MIN_VIRAL_SCORE` de 7 à 8 → moins d'enrichissements coûteux

## Support

Pas de support officiel. Tu as le code source complet, tu es libre de l'adapter.

Si tu es bloqué, ouvre Claude Code dans le dossier du projet et demande de l'aide — il a tout le contexte pour te diagnostiquer.

## Licence

MIT — fais-en ce que tu veux.
