"""Script à lancer UNE SEULE FOIS en local pour générer le token Gmail OAuth.

Usage :
    python setup_gmail.py

Prérequis :
    - Avoir téléchargé gmail_credentials.json depuis Google Cloud Console
    - L'avoir placé dans config/gmail_credentials.json

Résultat :
    - Génère config/gmail_token.json
    - Ce fichier contient le refresh token et permet de regénérer un access token automatiquement
"""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_PATH = Path("config/gmail_credentials.json")
TOKEN_PATH = Path("config/gmail_token.json")


def main() -> None:
    if not CREDENTIALS_PATH.exists():
        print(f"ERREUR : {CREDENTIALS_PATH} introuvable.")
        print("Télécharge-le depuis Google Cloud Console (voir NOTION_SETUP.md)")
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"Token sauvegardé dans {TOKEN_PATH}")
    print("Tu peux maintenant lancer python main.py ou déployer sur Railway.")


if __name__ == "__main__":
    main()
