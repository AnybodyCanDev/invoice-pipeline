# token_manager.py
import time
import requests
import config


def refresh_access_token():
    """Refresh the access token using the stored refresh token."""
    print("Making refresh token request to:", config.TOKEN_REFRESH_URL)
    payload = {
        "grant_type": "refresh_token",
        "client_id": config.ZOHO_CLIENT_ID,
        "client_secret": config.ZOHO_CLIENT_SECRET,
        "refresh_token": config.ZOHO_REFRESH_TOKEN
    }

    try:
        response = requests.post(config.TOKEN_REFRESH_URL, data=payload)
        print(f"Token refresh status: {response.status_code}")
        tokens = response.json()
        print("Token response:", tokens)

        if "access_token" in tokens:
            print("Access token refreshed successfully.")
            return tokens["access_token"]
        else:
            print("Error refreshing token:",
                  tokens.get("error", "Unknown error"))
            return None
    except Exception as e:
        print(f"Exception during token refresh: {str(e)}")
        return None


class ZohoTokenManager:
    def __init__(self):
        print("Initializing token manager and forcing refresh...")
        # Force refresh token on initialization
        new_token = refresh_access_token()
        if new_token:
            self.access_token = new_token
            self.expiration_time = time.time() + config.ACCESS_TOKEN_LIFESPAN
        else:
            print("WARNING: Could not refresh token, using token from config")
            self.access_token = config.ZOHO_ACCESS_TOKEN
            self.expiration_time = time.time() + config.ACCESS_TOKEN_LIFESPAN

    def get_access_token(self):
        # Refresh the token if it's within 5 minutes of expiring.
        if time.time() > self.expiration_time - 300:
            print("Token expiring soon, refreshing...")
            new_token = refresh_access_token()
            if new_token:
                self.access_token = new_token
                self.expiration_time = time.time() + config.ACCESS_TOKEN_LIFESPAN
            else:
                print("WARNING: Failed to refresh token!")
        return self.access_token


# Create a singleton instance
token_manager = ZohoTokenManager()


def get_auth_headers():
    """Return the headers for API calls with the latest access token."""
    token = token_manager.get_access_token()
    print(f"Using token: {token[:10]}... (truncated)")
    return {
        "Authorization": f"Zoho-oauthtoken {token}",
        "Content-Type": "application/json"
    }


if __name__ == "__main__":
    # For debugging: print the current access token
    print("Current Access Token:", token_manager.get_access_token())
