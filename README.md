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

## Le flow d'installation en deux phases

### Phase 1 — Créer tes comptes (1h à 1h30)

**Avant de toucher au code**, crée tes comptes et récupère tes clés API. Suis [ACCOUNTS_CHECKLIST.md](ACCOUNTS_CHECKLIST.md) dans l'ordre — c'est une checklist de 7 services avec liens directs et cases à cocher.

À la fin de cette phase tu auras :
- ✅ Clés API : Anthropic, OpenAI, Gemini, Notion, Supabase
- ✅ Fichier `gmail_credentials.json` téléchargé sur ta machine
- ✅ Adresse Gmail dédiée avec quelques newsletters IA déjà abonnées
- ✅ Compte Railway avec moyen de paiement

### Phase 2 — Installer avec Claude Code (30 min à 1h)

Une fois les comptes prêts, tu ouvres Claude Code et tu colles **un seul prompt**. Claude Code t'accompagne ensuite pas à pas :

- Vérif prérequis machine (Python, git, Railway CLI…)
- Création de l'environnement virtuel + install des dépendances
- Création du fichier `.env` avec tes clés
- Création de la database Notion (via API, zéro typo)
- Setup OAuth Gmail
- Test local sur 1 news pour valider
- Création de **ton propre repo GitHub privé**
- Déploiement Railway avec cron quotidien
- Publication de l'app Google Cloud en production

Suis [SETUP_WITH_CLAUDE.md](SETUP_WITH_CLAUDE.md).

## Documentation

| Fichier | Pour quoi |
|---|---|
| [README.md](README.md) | Vue d'ensemble (ce fichier) |
| [ACCOUNTS_CHECKLIST.md](ACCOUNTS_CHECKLIST.md) | **Phase 1** — Créer les comptes et obtenir les clés |
| [SETUP_WITH_CLAUDE.md](SETUP_WITH_CLAUDE.md) | **Phase 2** — Prompt à coller dans Claude Code pour l'installation technique |
| [INSTALL.md](INSTALL.md) | Alternative manuelle si tu ne veux pas utiliser Claude Code |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | FAQ et résolution des erreurs fréquentes |

## Coûts mensuels estimés

- Anthropic API (scoring + enrichissement web_search) : ~15 €
- OpenAI (gpt-image-2 pour les infographies) : ~43 €
- Gemini (carrousel Instagram) : ~10 €
- Railway (hébergement cron) : ~5 €
- Supabase (hébergement images) : gratuit
- **Total : ~70 € / mois** (pour ~10 infographies + 1 carrousel par jour)

Tu peux réduire :
- Baisser `MAX_NEWS_PER_DAY` de 10 à 5 → ~40 € / mois
- Désactiver le carrousel → ~55 € / mois
- Utiliser `gpt-image-1` au lieu de `gpt-image-2` → ~25 € / mois

## Support

Pas de support officiel. Tu as le code source complet, tu es libre de l'adapter.

Si tu es bloqué, ouvre Claude Code dans le dossier du projet et demande de l'aide — il a tout le contexte pour te diagnostiquer.

## Licence

MIT — fais-en ce que tu veux.
