import requests

# Use `.in` since your account is in India
url = "https://accounts.zoho.in/oauth/v2/token"

data = {
    "client_id": "1000.EQ66ZF5CU8YC5MT45RCOFGNE5BVQBK",
    "client_secret": "9a0f33a2d327203fa6c74f0efc04f1222b2e607f46",
    # Replace with your new code
    "code": "1000.5c6d0381a45e0f73e07123d1361795a7.46afc21f0682265cb6688a43d0e40477",
    "grant_type": "authorization_code",
    "redirect_uri": "http://localhost:8000"
}

response = requests.post(url, data=data)
print(response.json())  # Should return access_token and refresh_token
