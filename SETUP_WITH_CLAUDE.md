# Installation guidée par Claude Code

Ce repo contient un slash command Claude Code (`/onboard`) qui te guide pas à pas dans toute l'installation, **sans que tu aies besoin d'écrire un seul prompt** ni de comprendre le code.

## Pré-requis avant de lancer l'onboarding

1. Avoir créé tes 6 comptes (Anthropic, OpenAI, Google, Notion, Supabase, GitHub) — cf. [ACCOUNTS_CHECKLIST.md](ACCOUNTS_CHECKLIST.md).
2. Avoir installé Claude Code + un abonnement Claude Pro actif.
3. **Avoir connecté les MCPs Notion + Supabase à Claude Code** via `/mcp`. C'est ce qui permettra à Claude de créer la database Notion et le bucket Supabase pour toi sans que tu aies à toucher à leurs UIs.

> ⚠️ **Si les MCPs ne sont pas connectés**, `/onboard` t'arrêtera au moment de toucher à Notion/Supabase et te demandera de les connecter avant de continuer.

## Comment lancer l'onboarding

### Étape 1 — Cloner le repo

```bash
git clone https://github.com/deylac/veille-ia-starter.git veille-ia
cd veille-ia
```

### Étape 2 — Ouvrir Claude Code

```bash
claude
```

### Étape 3 — Lancer le slash command

Dans la session Claude Code, tape :

```
/onboard
```

C'est tout. Claude prend la main et te guide à travers les étapes :

1. ✅ Vérification Python 3.11+ et création du venv
2. ✅ Installation des dépendances Python
3. ✅ Création de ton `.env` (Claude te dit exactement quoi y mettre)
4. ✅ Anthropic — colle ta clé Claude API
5. ✅ OpenAI — colle ta clé gpt-image-2
6. ✅ Google Gemini — colle ta clé pour le carrousel
7. ✅ Notion — tu crées juste l'intégration + page parente, **Claude crée la database 12 propriétés via MCP Notion**
8. ✅ Supabase — **Claude crée le bucket via MCP Supabase**. 1 seule étape manuelle : coller 2 SQL dans le SQL Editor (~1 min, Claude affiche le contenu)
9. ✅ Création des sous-pages Notion automatiques (Coûts API + Rapport quotidien)
10. ✅ **Premier run réel** → ta 1re infographie publiée dans Notion 🎉
11. ✅ Déploiement Railway (optionnel) avec cron quotidien

## Pourquoi c'est mieux que l'install manuelle ?

| | Manuel ([INSTALL.md](INSTALL.md)) | Avec `/onboard` |
|---|---|---|
| Risque d'oublier une étape | élevé (10+ étapes) | nul (Claude vérifie chaque étape) |
| Risque de typo dans `.env` | élevé | nul (Claude écrit pour toi) |
| Création de la database Notion | toi, à la main, 11 propriétés à configurer | Claude le fait via MCP Notion |
| Création du bucket Supabase | toi, dans l'UI | Claude le fait via MCP Supabase |
| Risque de mauvais format SQL Supabase | possible | minimal (Claude affiche le SQL à coller) |
| Diagnostic d'erreur | grep + Stack Overflow | Claude lit l'erreur, propose le fix immédiatement |
| Durée totale | 1h30 - 2h | 30-45 min |
| Ton effort | concentration permanente | tu réponds aux questions de Claude |

## Pendant l'onboarding

Claude te demandera certaines infos en cours de route :
- Tes clés API au moment où tu viens de les créer (Anthropic, OpenAI, Gemini)
- Ta clé d'intégration Notion (`secret_…` ou `ntn_…`) après que tu l'aies créée
- L'URL de ta page Notion parente (Claude en extrait l'ID lui-même)
- Ton URL Supabase + service_role key

**Ce que Claude fait pour toi** (tu n'as RIEN à faire de ces choses) :
- Création de la database Notion avec ses 12 propriétés exactes (via MCP Notion)
- Création du bucket Supabase public (via MCP Supabase)
- Écriture de toutes les variables dans `.env`
- Création des sous-pages "Coûts API" et "Rapport quotidien" dans Notion

Si tu bloques sur une étape (ex: tu n'arrives pas à créer ta database Notion), demande simplement à Claude : « j'ai un problème pour créer la database », il te détaille.

## Si Claude ne te propose pas l'onboarding tout seul

Normalement, dès que tu ouvres Claude Code dans le repo cloné, il détecte que `.env` n'existe pas et te propose de lancer `/onboard`. S'il ne le fait pas :

1. Vérifie que tu es dans le bon dossier (`pwd` doit afficher le dossier `veille-ia/`)
2. Vérifie que le fichier `.claude/commands/onboard.md` existe
3. Force-le en tapant : `/onboard`

## Après l'installation

Quand l'onboarding est terminé, tu peux :
- Demander n'importe quoi à Claude : « modifie le seuil viral à 8 », « ajoute le RSS de The Verge », « pourquoi le run a échoué hier »
- Claude lit le code et `CLAUDE.md` automatiquement, donc il a tout le contexte

Pour les modifications profondes (ex: changer le design du template d'image), reste appuyé sur Claude — il a les bonnes pratiques internes (limites de longueur, palette, etc.) déjà documentées dans `CLAUDE.md`.

## Voir aussi

- [README.md](README.md) — Vue d'ensemble du projet
- [CLAUDE.md](CLAUDE.md) — Cartographie de l'app (lue auto par Claude Code)
- [.claude/commands/onboard.md](.claude/commands/onboard.md) — Le contenu exact du slash command, si tu veux comprendre ce que Claude va faire
- [INSTALL.md](INSTALL.md) — Installation 100 % manuelle si tu n'utilises pas Claude Code
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Si quelque chose casse après l'install
