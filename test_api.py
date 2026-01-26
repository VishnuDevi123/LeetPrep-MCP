import requests

response = requests.get("https://alfa-leetcode-api.onrender.com/select?titleSlug=two-sum")
print(response.json())