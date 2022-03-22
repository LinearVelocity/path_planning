import folium

from openrouteservice import client

import fiona as fn
from shapely.geometry import Polygon, mapping, MultiPolygon, LineString, Point
from shapely.ops import cascaded_union,unary_union

import pyproj
import osmnx as ox

# insert your ORS api key
api_key = '5b3ce3597851110001cf62489766727e63d84f6e8e2ea2b05ec3930f'
ors = client.Client(key=api_key)

# Twitter data from 2013
#tweet_file = 'tweets/tweets_magdeburg.shp'
tweet_file = 'high_risk_point.geojson'


# Function to create buffer around tweet point geometries and transform it to the needed coordinate system (WGS84)
def CreateBufferPolygon(point_in, resolution=2, radius=1000):
    sr_wgs = pyproj.Proj(init='epsg:4326')  # WGS84
    sr_utm = pyproj.Proj(init='epsg:32632')  # UTM32N
    point_in_proj = pyproj.transform(sr_wgs, sr_utm, *point_in)  # Unpack list to arguments
    point_buffer_proj = Point(point_in_proj).buffer(radius, resolution=resolution)  # 1000 m buffer
    # Iterate over all points in buffer and build polygon
    poly_wgs = []
    for point in point_buffer_proj.exterior.coords:
        poly_wgs.append(pyproj.transform(sr_utm, sr_wgs, *point))  # Transform back to WGS84
    return poly_wgs


# Function to request directions with avoided_polygon feature
def CreateRoute(avoided_point_list, n=0):
    route_request = {'coordinates': coordinates,
                     'format_out': 'geojson',
                     'profile': 'driving-car',
                     'preference': 'shortest',
                     'instructions': False,
                     'options': {'avoid_polygons': mapping(MultiPolygon(avoided_point_list))}}
    route_directions = ors.directions(**route_request)
    return route_directions


# Function to create buffer around requested route
def CreateBuffer(route_directions):
    line_tup = []
    for line in route_directions['features'][0]['geometry']['coordinates']:
        tup_format = tuple(line)
        line_tup.append(tup_format)
    new_linestring = LineString(line_tup)
    dilated_route = new_linestring.buffer(1)
    return dilated_route

map_tweet = folium.Map(tiles='Stamen Toner', location=([22.54475,114.05609]), zoom_start=14)  # Create map


def style_function(color):  # To style data
    return lambda feature: dict(color=color)


counter = 0
flood_tweets = []  # Flood affected tweets
tweet_geometry = []  # Simplify geometry of tweet buffer polygons
with fn.open(tweet_file, 'r') as tweet_data:  # Open data in reading mode
    print('{} tweets in total available.'.format(len(tweet_data)))
    for data in tweet_data:
        folium.Marker(list(reversed(data['geometry']['coordinates'])),
                          icon=folium.Icon(color='lightgray',
                                           icon_color='red',
                                           icon='twitter',
                                           prefix='fa'),
                          popup=data['properties']['name']).add_to(map_tweet)
        # Create buffer polygons around affected sites with 20 m radius and low resolution
        flood_tweet = CreateBufferPolygon(data['geometry']['coordinates'],
                                              resolution=2, 
                                              radius=1000)
        flood_tweets.append(flood_tweet)
        # Create simplify geometry and merge overlapping buffer regions
        poly = Polygon(flood_tweet)
        tweet_geometry.append(poly)
#union_poly = mapping(cascaded_union(tweet_geometry))
union_poly = mapping(unary_union(tweet_geometry))

folium.features.GeoJson(data=union_poly,
                        name='Flood affected areas',
                        style_function=style_function('#ffd699'), ).add_to(map_tweet)

#print('{} regular tweets with no flood information avalibale.'.format(counter))
print(len(flood_tweets), 'tweets with flood information available.')

# map_tweet.save(os.path.join('results', '1_tweets.html'))
map_tweet
map_tweet.save("map_2.html")


# Visualize start and destination point on map
#orig = ox.distance.nearest_nodes(map_tweet, X=114.01759, Y=22.53652)
#dest = ox.distance.nearest_nodes(G, X=114.08723, Y=22.55193)
coordinates = [[114.0415,22.5596], [114.05460,22.52222]]  # 高尔夫俱乐部 and 皇岗公园
for coord in coordinates:
    folium.map.Marker(list(reversed(coord))).add_to(map_tweet)
map_tweet.save("map_3.html")

# Regular Route
avoided_point_list = []  # Create empty list with avoided tweets

import requests
#from requests.adapters import HTTPAdapter
#from requests.packages.urllib3.util.retry import Retry
#session = requests.Session()
#retry = Retry(connect=3, backoff_factor=0.5)
#adapter = HTTPAdapter(max_retries=retry)
#session.mount('http://', adapter)
#session.mount('https://', adapter)
#session.get(url)

requests.adapters.DEFAULT_RETRIES = 5
s = requests.session()
s.keep_alive = False

route_directions = CreateRoute(avoided_point_list)  # Create regular route with still empty avoided_point_list

folium.features.GeoJson(data=route_directions,
                        name='Regular Route',
                        style_function=style_function('#ff5050'),
                        overlay=True).add_to(map_tweet)
print('Generated regular route.')
map_tweet.save("map_4.html")

# Avoiding tweets route
dilated_route = CreateBuffer(route_directions)  # Create buffer around route

# Check if flood affected tweet is located on route
try:
    for site_poly in flood_tweets:
        poly = Polygon(site_poly)
        if poly.within(dilated_route):
            avoided_point_list.append(poly)
            # Create new route and buffer
            route_directions = CreateRoute(avoided_point_list, 1)
            dilated_route = CreateBuffer(route_directions)
    folium.features.GeoJson(data=route_directions,
                            name='Alternative Route',
                            style_function=style_function('#006600'),
                            overlay=True).add_to(map_tweet)
    print('Generated alternative route, which avoids affected areas.')
except Exception:
    print('Sorry, there is no route available between the requested destination because of too many blocked streets.')
map_tweet.save("map_5.html")
# map_tweet.save(os.path.join('results', '2_routes.html'))
map_tweet.add_child(folium.map.LayerControl())
map_tweet
map_tweet.save("map_6.html")
