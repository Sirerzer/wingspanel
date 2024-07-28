import requests
import yml
def create(uuid):
    url = yml.remote+'api/application/servers/external/'+uuid
    headers = {
        "Authorization": "Bearer " + yml.token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "cookie": "pterodactyl_session=eyJpdiI6InhIVXp5ZE43WlMxUU1NQ1pyNWRFa1E9PSIsInZhbHVlIjoiQTNpcE9JV3FlcmZ6Ym9vS0dBTmxXMGtST2xyTFJvVEM5NWVWbVFJSnV6S1dwcTVGWHBhZzdjMHpkN0RNdDVkQiIsIm1hYyI6IjAxYTI5NDY1OWMzNDJlZWU2OTc3ZDYxYzIyMzlhZTFiYWY1ZjgwMjAwZjY3MDU4ZDYwMzhjOTRmYjMzNDliN2YifQ%253D%253D"
    }

    response = requests.request('GET', url, headers=headers)
    print(response.text)