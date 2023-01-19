import requests
import json
import icalendar
import datetime
import hashlib
import time

OFFSET = -time.timezone
events_url = "https://bitlair.nl/Special:Ask/-5B-5BCategory:Event-5D-5D-20-5B-5BStart::%E2%89%A519-20January-202023-5D-5D/-3FStart/-3FEnd/-3FEvent-20location/mainlabel%3D/limit%3D50/order%3DASC/sort%3DStart/prettyprint%3Dtrue/format%3Djson"
# above URL asks for all events and returns their name, start, end and location
events_page = requests.get(events_url)
# remove first line from output because the first line is '<script src='/vendor/composer/installed.js'></script>'
# which is not valid JSON, believe it or not
events = json.loads(''.join(events_page.text.splitlines(keepends=True)[1:]))

cal = icalendar.Calendar()

# Some properties are required to be compliant
cal.add('prodid', '-//Bitlair event calendar//bitlair.nl//')
cal.add('version', '2.0')

for key, value in events['results'].items():
    # unix timestamps from semwiki are not in UTC but in $localtime
    start_time = int(value['printouts']['Start'][0]['timestamp']) - OFFSET
    end_time = int(value['printouts']['End'][0]['timestamp']) - OFFSET

    # remove preceding 'Events/YYYY-MM-DD ' from pagename to result in the actual event name
    eventname = key[18:]

    event = icalendar.Event()
    event.add('summary', eventname)
    
    event.add('description', f'{key}\n {value["fullurl"]}')
    event.add('dtstamp', datetime.datetime.now())
    event.add('dtstart', datetime.datetime.fromtimestamp(start_time))
    event.add('dtend', datetime.datetime.fromtimestamp(end_time))
    event.add('url', value['fullurl'])
    event['location'] = icalendar.vText(value['printouts']['Event location'][0]['fulltext'])
    
    url_hash_substr = hashlib.md5(value["fullurl"].encode()).hexdigest()[0:10]
    # we need to use something that is relatively safe as a UID, so use the first 10 characters of the hexdigest of the wikiurl
    event['uid'] = f'{url_hash_substr}@bitlair.nl'
    
    # Add the event to the calendar
    cal.add_component(event)


f = open('output.ics', 'wb')
f.write(cal.to_ical())
f.close()