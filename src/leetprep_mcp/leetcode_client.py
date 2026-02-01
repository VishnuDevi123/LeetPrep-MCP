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

def fetch_user_stats(username: str) -> dict:
    """
    Fetch user stats from alfa-leetcode-api.
    
    Args:
        username: LeetCode username
    Returns: user stats as a dict
    """
    response = requests.get(f"{ALFA_API_BASE}/{username}/stats")
    if response.status_code != 200:
        return {"error": True, "message": f"API returned status {response.status_code}"}
    return response.json()

def fetch_submissions(username: str, limit: int = 20) -> dict:
    """
    Fetch recent submissions for a user from alfa-leetcode-api.
    
    Args:
        username: LeetCode username
        limit: Number of recent submissions to fetch
    Returns: recent submissions as a dict
    """
    response = requests.get(f"{ALFA_API_BASE}/{username}/submissions?limit={limit}")
    if response.status_code != 200:
        return {"error": True, "message": f"API returned status {response.status_code}"}
    return response.json()

def fetch_profile(username: str) -> dict:
    """
    Fecth user profile information from alfa-leetcode-api.
    Args:
        username (str): _description_

    Returns:
        dict: _description_
    """
    response = requests.get(f"{ALFA_API_BASE}/{username}/profile")
    if response.status_code != 200:
        return {"error": True, "message": f"API returned status {response.status_code}"}
    return response.json()