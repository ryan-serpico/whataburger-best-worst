import json
import os
import re
import sys

import googlemaps
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Get your api key from the Google Cloud console: https://console.cloud.google.com/apis/credentials
gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))

cid_regex = re.compile(r'(https:\/\/maps.google.com\/\?cid=)(\d+)')

whataburer_list = []

def getSoup(url):
    page = requests.get(url) 
    soup = BeautifulSoup(page.content, 'html.parser')
    return soup

# Use bs4 to scrape location info from each city page
def get_city_locations(url):
    soup = getSoup(url)

    try:
        result_list = soup.find('ol', class_='ResultList')

        result_items = result_list.find_all('li', class_='ResultList-item')


        for item in result_items:
            try:
                location_nickname = item.find('span', class_='LocationName-nickname').text
            except AttributeError:
                location_nickname = None
            location_name = item.find('span', class_='LocationName-displayName').text
            location_address_1 = item.find('span', class_='c-address-street-1').text
            address_row = item.find_all('div', class_='c-AddressRow')[1]
            location_address_2 = ' '.join([x.text for x in address_row.find_all('span')])
            location_full_address = ', '.join([location_address_1, location_address_2])
            location_city = item.find('span', class_='c-address-city').text
            location_state = item.find('span', class_='c-address-state').text
            google_maps_url = item.find('a', class_='c-get-directions-button').get('href')
            try:
                cid = cid_regex.search(google_maps_url).group(2)
            except AttributeError:
                cid = None


            whataburer_list.append({
                'location_nickname': location_nickname,
                'location_name': location_name,
                'location_address_1': location_address_1,
                'location_address_2': location_address_2,
                'location_full_address': location_full_address,
                'location_city': location_city,
                'location_state': location_state,
                'google_maps_url': google_maps_url,
                'cid': cid
            })

    except:
        try:
            location_nickname = soup.find('span', class_='Banner-titleGeo').text
            location_name = soup.find('span', id='location-name').text
            location_address_1 = soup.find('span', class_='c-address-street-1').text
            address_row = soup.find_all('div', class_='c-AddressRow')[1]
            location_address_2 = ' '.join([x.text for x in address_row.find_all('span')])
            location_full_address = ', '.join([location_address_1, location_address_2])
            location_city = soup.find('span', class_='c-address-city').text
            location_state = soup.find('span', class_='c-address-state').text
            google_maps_url = soup.find('a', class_='c-get-directions-button').get('href')
            try:
                cid = cid_regex.search(google_maps_url).group(2)
            except AttributeError:
                cid = None

            whataburer_list.append({
                'location_nickname': location_nickname,
                'location_name': location_name,
                'location_address_1': location_address_1,
                'location_address_2': location_address_2,
                'location_full_address': location_full_address,
                'location_city': location_city,
                'location_state': location_state,
                'google_maps_url': google_maps_url,
                'cid': cid
            })
        except Exception as e:
            print(url)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

# Use bs4 to scrape city urls from each state page
def get_cities(url):
    soup = getSoup(url)
    city_link_list = soup.find_all('a', class_='Directory-listLink')
    city_link_list = ['https://locations.whataburger.com/' + x.get('href') for x in city_link_list]
    for city in city_link_list:
        try:
            get_city_locations(city)
        except Exception as e:
            print(e)
            pass

# Use bs4 to scrape state urls
def get_states(url):
    soup = getSoup(url)
    state_link_list = soup.find_all('a', class_='Directory-listLink')
    state_link_list = ['https://locations.whataburger.com/' + x.get('href') for x in state_link_list]
    for state in state_link_list:
        print(state)
        try:
            get_cities(state)
        except Exception as e:
            print(e)
            pass

# After we have our dataframe of locations, we can pull ratings from Google Maps.
def get_google_maps_ratings(place_name):
    place_result = gmaps.places(place_name)
    place_id = place_result['results'][0]['place_id']

    place = gmaps.place(place_id = place_id)

    rating = place['result']['rating']
    total_ratings = place['result']['user_ratings_total']
    return rating, total_ratings

get_states('https://locations.whataburger.com/directory.html/')

df = pd.DataFrame(whataburer_list)

print('Getting ratings...')

# Run a for loop through the dataframe and get the google maps ratings and rating totals for each location_full_address
for index, row in df.iterrows():
    try:
        rating, total_ratings = get_google_maps_ratings('Whataburger' + row['location_full_address'])
        df.at[index, 'rating'] = rating
        df.at[index, 'total_ratings'] = total_ratings
    except Exception as e:
        print(row['location_full_address'])
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        df.at[index, 'rating'] = None
        df.at[index, 'total_ratings'] = None
        pass

df.to_csv('output/whataburger_locations.csv', index=False)

print('Done!')

