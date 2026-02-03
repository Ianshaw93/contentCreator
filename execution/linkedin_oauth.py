"""
LinkedIn OAuth 2.0 flow - run once to get access token.
"""
import os
import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = ["openid", "profile", "w_member_social"]
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "..", ".linkedin_tokens.json")

auth_code = None


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)

        if parsed.path == "/callback":
            query = parse_qs(parsed.query)

            if "code" in query:
                auth_code = query["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Success!</h1><p>You can close this window.</p>")
            elif "error" in query:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                error = query.get("error_description", ["Unknown error"])[0]
                self.wfile.write(f"<h1>Error</h1><p>{error}</p>".encode())
            else:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Error</h1><p>No code received</p>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logging


def get_auth_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
    }
    return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"


def exchange_code_for_token(code):
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()


def get_user_info(access_token):
    """Get the user's LinkedIn ID (person URN)."""
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def save_tokens(token_data, user_info):
    tokens = {
        "access_token": token_data["access_token"],
        "expires_in": token_data.get("expires_in"),
        "person_id": user_info.get("sub"),  # This is the person ID from OpenID
    }
    if "refresh_token" in token_data:
        tokens["refresh_token"] = token_data["refresh_token"]

    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

    print(f"Tokens saved to {TOKEN_FILE}")
    return tokens


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Error: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env")
        return

    global auth_code

    # Generate and open auth URL
    auth_url = get_auth_url()
    print(f"Opening browser for authorization...")
    print(f"If browser doesn't open, visit: {auth_url}")
    webbrowser.open(auth_url)

    # Start local server to catch callback
    print("Waiting for authorization callback on localhost:8080...")
    server = HTTPServer(("localhost", 8080), OAuthHandler)

    while auth_code is None:
        server.handle_request()

    server.server_close()
    print(f"Got authorization code!")

    # Exchange code for token
    print("Exchanging code for access token...")
    token_data = exchange_code_for_token(auth_code)

    # Get user info (person ID)
    print("Getting user info...")
    user_info = get_user_info(token_data["access_token"])

    # Save tokens
    tokens = save_tokens(token_data, user_info)

    print(f"\nSuccess! LinkedIn OAuth complete.")
    print(f"Person ID: {tokens['person_id']}")
    print(f"Token expires in: {tokens.get('expires_in', 'unknown')} seconds")


if __name__ == "__main__":
    main()
