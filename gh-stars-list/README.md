# GitHub Stars Organizer

A Python tool that helps organize your GitHub starred repositories into lists/collections using AI categorization.

## Setup

1. Install dependencies:

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install requests ollama-python
```

2. Make sure Ollama is running locally with llama3.2:3b model:

```bash
ollama run llama3.2:3b
```

3. Get your GitHub personal access token with these permissions:
   - `read:user`
   - `repo`
   - `write:collections`

## Usage

1. First, fetch your starred repositories:

```bash
python main.py get_starred_repos --username YOUR_USERNAME --token YOUR_GITHUB_TOKEN
```

2. Then categorize them using AI:

```bash
python main.py categorize
```

The script will:

- Fetch and store your GitHub stars
- Use Ollama to suggest categories for each repository
- Create new lists and add repositories to appropriate categories

## Requirements

- Python 3.8+
- Ollama with llama3.2:3b model
- GitHub Personal Access Token
