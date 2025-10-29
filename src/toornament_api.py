import requests
import json
import datetime

headers = {
    'Range':'matches=0-100',
}

response = requests.get('https://play.toornament.com/api/matches?tournament_ids=8615818184858034176&statuses=pending&sort=scheduled_asc', headers=headers)
print(response.status_code)
data = response.json()

current_date = datetime.datetime.now(datetime.timezone.utc)
current_date = datetime.datetime(current_date.year, 8, 9, 15, 0, 0, tzinfo=datetime.timezone.utc)

close_matches = []


for match in data:
    # check if the scheduledDatetime is in +- 2 hours from now
    scheduled_datetime = datetime.datetime.fromisoformat(match['scheduledDatetime'].replace('Z', '+00:00'))
    if abs((scheduled_datetime - current_date).total_seconds()) <= 7200:
        close_matches.append({
            'id': match['id'],
            'scheduledDatetime': scheduled_datetime.isoformat(),
            'team1': match['opponents'][0]['participant'],
            'team2': match['opponents'][1]['participant'],
            'status': match['status'],
            'stagename': match['group']['name'],
            'round': match['round']['name']
        })

print(close_matches)
print(f"Number of close matches: {len(close_matches)}")

class ToornamentAPI:
    def __init__(self):
        self.base_url = 'https://play.toornament.com/api/matches?tournament_ids=8615818184858034176&statuses=pending&sort=scheduled_asc'
        self.headers = {
            'Range': 'matches=0-100',
        }

    def get_matches(self):
        response = requests.get(self.base_url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()