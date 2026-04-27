"""Script à lancer UNE SEULE FOIS en local pour créer la sous-page Notion 'Coûts API'.

Étapes :
1. Vérifier que NOTION_PARENT_PAGE_ID est dans .env (ID de la page parente
   où tu veux créer la sous-page — ex: ta page "Veille IA Superproductif").
2. Vérifier que ton intégration Notion est partagée sur cette page parente.
3. Lancer : `python setup_cost_report_page.py`
4. Copier l'ID affiché et l'ajouter à ton .env comme NOTION_COST_REPORT_PAGE_ID
   (et dans Railway via les variables d'env).
"""
import logging
import os
import sys

from publish.notion_cost_report import create_cost_report_page


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID", "").strip()
    if not parent_page_id:
        print("ERREUR : la variable d'env NOTION_PARENT_PAGE_ID est manquante.")
        print("Ajoute dans ton .env la ligne suivante (ID de la page parente, sans tirets) :")
        print("  NOTION_PARENT_PAGE_ID=34b76dcb9c4e809e95aac845c41aa4c7")
        print("Puis relance ce script.")
        return 1

    print(f"Création de la sous-page sous la page parente {parent_page_id}...")
    try:
        page_id = create_cost_report_page(parent_page_id)
    except Exception as e:
        print(f"\nERREUR lors de la création : {type(e).__name__} : {e}")
        print("Vérifie que ton intégration Notion est bien partagée sur la page parente.")
        return 2

    print()
    print("=" * 70)
    print("✅ Sous-page Notion créée.")
    print()
    print(f"ID de la page : {page_id}")
    print()
    print("⚠️  AJOUTE CETTE LIGNE À TON .env (et à Railway) :")
    print(f"   NOTION_COST_REPORT_PAGE_ID={page_id}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
