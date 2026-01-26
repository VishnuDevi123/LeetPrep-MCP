import requests

ALFA_API_BASE = "https://alfa-leetcode-api.onrender.com"

def fetch_problem(slug: str) -> dict:
    """
    Fetch problem details from alfa-leetcode-api.
    
    Args:
        slug: Problem URL slug (e.g., 'two-sum')
    
    Returns:
        dict with problem details formatted for our database
    """
    # 1. Call the API
    response = requests.get(f"{ALFA_API_BASE}/select?titleSlug={slug}")
    
    # 2. Check for errors
    if response.status_code != 200:
        return {"error": True, "message": f"API returned status {response.status_code}"}
    
    data = response.json()
    
    # 3. Extract and format the fields we need
    # TODO: You need to figure out the exact field names from the API response
    # and map them to your database schema
    
    patterns = [tag["name"] for tag in data.get("topicTags", [])]
    return {
        "leetcode_id": data.get("questionId"),  # Extract from data
        "title": data.get("questionTitle"),        # Extract from data
        "slug": data.get("titleSlug"),         # Extract from data  
        "difficulty": data.get("difficulty"),   # Extract from data
        "patterns": patterns,     # Extract from topicTags
        "companies":[],    # Extract if available
    }