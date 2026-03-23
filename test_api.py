"""quick manual api probe for the problem lookup endpoint."""

import requests

# direct request to verify the external provider responds with valid json.
response = requests.get("https://alfa-leetcode-api.onrender.com/select?titleSlug=two-sum")
print(response.json())
