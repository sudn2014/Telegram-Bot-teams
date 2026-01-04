import csv
import requests
import json
from datetime import datetime, timedelta
from msal import ConfidentialClientApplication

# Env vars
client_id = os.environ['AZURE_CLIENT_ID']
client_secret = os.environ['AZURE_CLIENT_SECRET']
tenant_id = os.environ['AZURE_TENANT_ID']
community_id = os.environ['TEAMS_COMMUNITY_ID']
git_token = os.environ.get('GIT_TOKEN')  # For CSV fetch

# Fetch CSV from GitHub
def fetch_csv():
    headers = {'Authorization': f'token {git_token}'}
    response = requests.get('https://api.github.com/repos/sudn2014/telegram-bot-teams/contents/pending_teams.csv', headers=headers)
    if response.status_code == 200:
        content_b64 = response.json()['content']
        content = base64.b64decode(content_b64).decode('utf-8')
        return list(csv.DictReader(content.splitlines()))
    return []

# Extract today's emails (Timestamp >= today 00:00)
today = datetime.now().date()
new_emails = []
for row in fetch_csv():
    row_date = datetime.strptime(row['Timestamp'], '%Y-%m-%d %H:%M:%S').date()
    if row_date == today and row['Email'] not in [e['Email'] for e in new_emails]:
        new_emails.append({'email': row['Email'], 'name': row['Name']})

print(f"Found {len(new_emails)} new emails for today")

# Auth for Microsoft Graph
scopes = ["https://graph.microsoft.com/.default"]
app = ConfidentialClientApplication(
    client_id, authority=f"https://login.microsoftonline.com/{tenant_id}",
    client_credential=client_secret
)
result = app.acquire_token_silent(scopes, account=None)
if not result:
    result = app.acquire_token_for_client(scopes)
token = result['access_token']

# Add to Teams community (invite as members)
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
for user in new_emails:
    body = {
        'members': [{
            'email': user['email'],
            'displayName': user['name'],
            'roles': ['member']
        }]
    }
    response = requests.post(f"https://graph.microsoft.com/v1.0/groups/{community_id}/members/$ref", headers=headers, json=body)
    if response.status_code in [200, 201, 204]:
        print(f"Added {user['name']} ({user['email']}) to Teams community")
    else:
        print(f"Failed to add {user['email']}: {response.status_code} - {response.text}")

print("Daily processing complete")
