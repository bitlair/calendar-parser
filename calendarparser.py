#!/usr/bin/env python3

import requests
import json
import icalendar
from datetime import datetime, timedelta
import hashlib
import time
import re
import sys

OFFSET = -time.timezone
events_url = "https://bitlair.nl/Special:Ask/-5B-5BCategory:Event-5D-5D-20-5B-5BStart::%E2%89%A519-20August-202024-5D-5D/-3FStart/-3FEnd/-3FStatus/-3FEvent-20location/mainlabel%3D/limit%3D50/order%3DASC/sort%3DStart/prettyprint%3Dtrue/format%3Djson"
# above URL asks for all events and returns their name, start, end and location
events_page = requests.get(events_url)
events = events_page.json()

cal = icalendar.Calendar()

# Some properties are required to be compliant
cal.add('prodid', '-//Bitlair event calendar//bitlair.nl//')
cal.add('version', '2.0')

for page_path, value in events['results'].items():
    # Unix timestamps from semwiki are not in UTC but in $localtime
    start_time = None
    end_time = None
    if (tt := value['printouts']['Start']) and tt:
        start_time = datetime.fromtimestamp(int(tt[0]['timestamp']) - OFFSET)
    if (tt := value['printouts']['End']) and tt:
        end_time = datetime.fromtimestamp(int(tt[0]['timestamp']) - OFFSET)

    if not start_time:
        continue
    if not end_time:
        end_time = start_time + timedelta(hours=4)

    # Remove preceding 'Events/YYYY-MM-DD ' if existant from pagename to result in the actual event name
    eventname = page_path
    if (m := re.search(r"Events\/....-..-.. (.*)", page_path)) and m:
        eventname = m[1]

    # If an event ends when humans are usually asleep, truncate the time range to midnight.
    # This prevents calendar items from cluttering the next day when viewed.
    if end_time.hour < 6:
        end_time = datetime(end_time.year, end_time.month, end_time.day, 23, 59) - timedelta(days=1)

    event = icalendar.Event()
    event.add('summary', eventname)

    event.add('description', f'{page_path}\n {value["fullurl"]}')
    event.add('dtstamp', datetime.now())
    event.add('dtstart', start_time)
    event.add('dtend', end_time)
    event.add('url', value['fullurl'])
    event['location'] = icalendar.vText(value['printouts']['EventLocation'][0]['fulltext'])

    if len(value['printouts']['Status']) != 0:
        # a status is defined, see if we can parse it to a status as per RFC5545 3.8.1.11
        status_value = value['printouts']['Status'][0]['fulltext'].upper()

        # use a few synonyms in Dutch and English just to be sure
        if status_value in ("CANCELED", "CANCELLED"): # damn 'muricans!
            event['status'] = 'CANCELLED'
        elif status_value in ("TENTATIVE", "TBD", "MAYBE", "NNB", "NTB", "NOG NIET BEKEND"): 
            event['status'] = 'TENTATIVE'
        elif status_value in ("CONFIRMED", "DEFINITIVE", "DEFINITIEF", "BEVESTIGD"):
            event['status'] = 'CONFIRMED'

    url_hash_substr = hashlib.md5(value["fullurl"].encode()).hexdigest()[0:10]
    # we need to use something that is relatively safe as a UID, so use the first 10 characters of the hexdigest of the wikiurl
    event['uid'] = f'{url_hash_substr}@bitlair.nl'

    # Add the event to the calendar
    cal.add_component(event)


f = open(sys.argv[1], 'wb')
f.write(cal.to_ical())
f.close()
