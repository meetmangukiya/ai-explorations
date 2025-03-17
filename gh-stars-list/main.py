import requests
import json
import ollama
from typing import List, Dict
import time
from pydantic import BaseModel
from typing import List, Dict

class GitHubStarsOrganizer:
    def __init__(self, username: str, token: str):
        self.username = username
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def get_starred_repos(self) -> List[Dict]:
        stars = []
        page = 1

        while True:
            print("getting page", page)
            url = f"https://api.github.com/users/{self.username}/starred?page={page}&per_page=100"
            response = requests.get(url, headers=self.headers)

            if response.status_code != 200:
                print(f"Error fetching stars: {response.status_code}")
                break

            repositories = response.json()
            if not repositories:
                break

            for repo in repositories:
                stars.append({
                    'name': repo['full_name'],
                    'description': repo['description'] or "",
                    'url': repo['html_url'],
                    'language': repo['language'],
                    'topics': repo.get('topics', [])
                })

            page += 1

        return stars

    def get_existing_lists(self) -> List[Dict]:
        url = "https://api.github.com/graphql"
        query = """
        query($username: String!) {
          user(login: $username) {
            lists(first: 100) {
              nodes {
                id
                name
                description
              }
            }
          }
        }
        """
        response = requests.post(
            url,
            headers=self.headers,
            json={
                'query': query,
                'variables': {'username': self.username}
            }
        )

        if response.status_code != 200:
            print(f"Error fetching collections: {response.status_code}")
            return []

        data = response.json()
        print("existing lists json", data)
        return data.get('data', {}).get('user', {}).get('lists', {}).get('nodes', [])

    def create_list(self, name: str, description: str) -> Dict:
        url = "https://api.github.com/collections"
        data = {
            "name": name,
            "description": description,
            "private": False
        }

        response = requests.post(url, headers=self.headers, json=data)

        if response.status_code != 201:
            print(f"Error creating list: {response.status_code}")
            return None

        return response.json()

    def add_repo_to_list(self, collection_id: str, repo_full_name: str) -> bool:
        url = f"https://api.github.com/collections/{collection_id}/repositories"
        data = {
            "repository_full_name": repo_full_name
        }

        response = requests.put(url, headers=self.headers, json=data)
        return response.status_code == 204

# Define the schema for AI response using Pydantic
class ListSuggestion(BaseModel):
    lists: List[str]
    confidence: float
    reasoning: str | None = None

def categorize_with_ai(repo: Dict, existing_lists: List[Dict]) -> List[str]:
    # Prepare the context for AI
    existing_list_names = [lst['name'] for lst in existing_lists]
    existing_lists_str = ", ".join(existing_list_names) if existing_list_names else "No existing lists"

    # Define the format schema for structured output
    format_schema = {
        "type": "object",
        "properties": {
            "lists": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "maxItems": 3
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "reasoning": {
                "type": "string"
            }
        },
        "required": ["lists", "confidence"]
    }

    # Create the prompt
    prompt = f"""
    Analyze this GitHub repository and suggest appropriate lists to categorize it:

    Repository Details:
    - Name: {repo['name']}
    - Description: {repo['description']}
    - Language: {repo['language']}
    - Topics: {', '.join(repo['topics'])}

    Existing lists: {existing_lists_str}

    Return up to 3 most appropriate list names (can be existing or new ones).
    """

    try:
        # Call Ollama with structured output
        response = ollama.chat(
            model="llama3.2:3b",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            format=format_schema,
            options={"temperature": 0}  # More deterministic output
        )

        # Parse the response using Pydantic
        suggestion = ListSuggestion.model_validate_json(response.message.content)

        # Log the results
        print(f"Suggested lists: {suggestion.lists}")
        print(f"Confidence: {suggestion.confidence}")
        if suggestion.reasoning:
            print(f"Reasoning: {suggestion.reasoning}")

        return suggestion.lists

    except Exception as e:
        print(f"Error during AI categorization: {str(e)}")
        return []

def main():
    import argparse

    parser = argparse.ArgumentParser(description='GitHub Stars Organizer')
    parser.add_argument('action', choices=['get_starred_repos', 'categorize'],
                       help='Action to perform')
    parser.add_argument('--username', required=False, help='GitHub username')
    parser.add_argument('--token', required=False, help='GitHub personal access token')
    args = parser.parse_args()

    if not args.username or not args.token:
        parser.error("--username and --token arguments are required")

    organizer = GitHubStarsOrganizer(args.username, args.token)

    if args.action == 'get_starred_repos':
        # Get and store starred repos
        print("Fetching starred repositories...")
        starred_repos = organizer.get_starred_repos()

        with open('github_stars.json', 'w') as f:
            json.dump(starred_repos, f, indent=2)
        print("Stored starred repositories in github_stars.json")

    elif args.action == 'categorize':
        # Read starred repos from JSON file
        print("Reading starred repositories from file...")
        with open('github_stars.json', 'r') as f:
            starred_repos = json.load(f)

        print("Fetching existing lists...")
        existing_lists = organizer.get_existing_lists()
        print("existing lists: ", existing_lists)

        # Dictionary to store categorizations
        categorizations = {}

        # Process each starred repository
        for repo in starred_repos:
            print(f"\nProcessing {repo['name']}...")

            # Get AI suggestions
            suggested_lists = categorize_with_ai(repo, existing_lists)
            print("suggeseted lists for repo", repo['name'], suggested_lists)

            # Rate limiting pause
            time.sleep(1)

        print("\nCompleted organizing starred repositories!")

if __name__ == "__main__":
    main()
