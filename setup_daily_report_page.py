"""À lancer UNE FOIS en local pour créer la sous-page Notion 'Rapport quotidien'.

Étapes :
1. Vérifier que NOTION_PARENT_PAGE_ID est dans .env (ID de "Veille IA Superproductif").
2. Vérifier que ton intégration Notion est partagée sur la page parente.
3. Lancer : python setup_daily_report_page.py
4. Copier l'ID affiché dans .env (et Railway) sous NOTION_DAILY_REPORT_PAGE_ID.

Optionnel : applique aussi la migration observability/migrations/002_daily_runs.sql
dans Supabase SQL editor pour activer la persistance des runs.
"""
import logging
import os
import sys

from publish.notion_daily_report import create_daily_report_page


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID", "").strip()
    if not parent_page_id:
        print("ERREUR : NOTION_PARENT_PAGE_ID manquant dans .env")
        print("Ajoute :  NOTION_PARENT_PAGE_ID=34b76dcb9c4e809e95aac845c41aa4c7")
        return 1

    print(f"Création de la sous-page rapport quotidien sous {parent_page_id}...")
    try:
        page_id = create_daily_report_page(parent_page_id)
    except Exception as e:
        print(f"\nERREUR : {type(e).__name__} : {e}")
        print("Vérifie que ton intégration Notion est partagée sur la page parente.")
        return 2

    print()
    print("=" * 70)
    print("✅ Sous-page rapport quotidien créée.")
    print()
    print(f"ID : {page_id}")
    print()
    print("⚠️  AJOUTE CETTE LIGNE À TON .env (et à Railway) :")
    print(f"   NOTION_DAILY_REPORT_PAGE_ID={page_id}")
    print()
    print("⚠️  N'oublie pas d'appliquer la migration SQL dans Supabase :")
    print("   observability/migrations/002_daily_runs.sql")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
