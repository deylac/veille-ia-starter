# Veille IA — Ton pipeline automatique de veille IA quotidienne

Chaque matin à 6 h, ton bot récupère les news IA les plus importantes du jour et les transforme automatiquement en :

- **Des infographies éditoriales premium** (style magazine print) — une par news
- **Un carrousel Instagram** (cover + slides news + outro) — un par jour

Tout arrive dans ta base Notion, prêt à valider et publier sur LinkedIn / Instagram.

Tu paies tes propres APIs (~70 €/mois pour ~10 infographies + 1 carrousel par jour). Le code tourne sur TON Railway, avec TES clés. Zéro dépendance, zéro abonnement SaaS à vie.

## Comment ça marche

```
Cron Railway 6 h Paris
        |
        v
  RSS officiels (Anthropic, OpenAI, Google, DeepMind, Mistral, HF)
  Newsletters IA (Gmail API)
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

## 🚀 Installation guidée par Claude Code (recommandé)

Ce repo est conçu pour être installé en mode "guidé" par Claude Code — pas besoin de comprendre tout le code.

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
6. Setup Notion (intégration + database + page parente)
7. Setup Supabase (projet + bucket public + 2 migrations SQL)
8. Création des 2 sous-pages Notion automatiques (Coûts API + Rapport quotidien)
9. **Premier run de test** → ta 1re infographie publiée dans Notion 🎉
10. Déploiement Railway (optionnel) pour le cron quotidien

**Tu n'as RIEN à savoir techniquement** — Claude vérifie chaque étape avant de continuer et t'aide en cas de blocage.

### Préparer en amont (optionnel)

Si tu veux gagner du temps avant l'onboarding, tu peux créer en avance les comptes externes : suis [ACCOUNTS_CHECKLIST.md](ACCOUNTS_CHECKLIST.md). Sinon Claude t'envoie directement les bons liens au moment voulu.

### Installation manuelle (sans Claude Code)

Si tu préfères, tout est aussi décrit dans [INSTALL.md](INSTALL.md).

## Documentation

| Fichier | Pour quoi |
|---|---|
| [README.md](README.md) | Vue d'ensemble (ce fichier) |
| [CLAUDE.md](CLAUDE.md) | Cartographie complète de l'app (architecture, modules, conventions) — lu auto par Claude Code |
| [.claude/commands/onboard.md](.claude/commands/onboard.md) | Workflow d'installation guidée — déclenché par `/onboard` |
| [ACCOUNTS_CHECKLIST.md](ACCOUNTS_CHECKLIST.md) | Liste des comptes externes à créer (avec liens directs) |
| [INSTALL.md](INSTALL.md) | Installation manuelle (sans Claude Code) |
| [SETUP_WITH_CLAUDE.md](SETUP_WITH_CLAUDE.md) | Notes complémentaires pour l'installation guidée |
| [NOTION_SETUP.md](NOTION_SETUP.md) | Création de la base Notion + propriétés |
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
