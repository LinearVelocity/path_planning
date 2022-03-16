#01
from __future__ import print_function
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

import osmnx as ox
import requests
import json
import networkx as nx
from IPython.display import IFrame
import folium
import numpy as np
#02
G = ox.graph_from_place('福田区', network_type='all', which_result=2)
ox.save_graphml(G, filepath=r'Documents/route_planner/results/road_network/futianqu.graphml')
#03
G = ox.load_graphml(filepath=r'Documents/route_planner/results/road_network/futianqu.graphml')
#04
ox.plot_graph(G,edge_linewidth=1)
#05
overpass_url = "http://overpass-api.de/api/interpreter"
overpass_query = """
[out:json];
area["name"="福田区"]->.a;
(
  node["tourism"~"viewpoint|zoo|theme_park|museum|hotel|attraction|gallery|aquarium"]["name"](area.a);
  node["amenity"~"."]["name"](area.a);
  node["building"~"accommodation|commercial|civic/amenity|sports"]["name"](area.a);
);
  node["office"~"."]["name"](area.a);
  node["shop"~"."]["name"](area.a);
out center;                                                                                                                       
"""

response = requests.get(overpass_url,params={'data': overpass_query})
data = response.json()

with open('places.json', 'w') as outfile:
    json.dump(data, outfile)
#POI 列表保存到文件  

with open('places.json', 'r') as f:
    data = json.load(f)
#从文件读取 POI 列表

#06
places = []
counter = 0
for element in data['elements']:
    places.append(element);
    print(str(counter) + "-" + element["tags"]["name"])
    counter+=1
#07
print("请写下您的选择，并用逗号隔开：");
selections = input();
selected_indexes = [int(d) for d in selections.split(',')]

user_places = []
for place_index in selected_indexes:
    user_places.append(places[place_index])
    print(places[place_index]);
#08
m = folium.Map(location=[22.5429,114.0591])
#08.5
gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)
#09
nearest_nodes = []
for place in user_places:
    point_X = place["lon"]
    point_Y = place["lat"]
    print(place["tags"]["name"])
    #nearest = ox.utils.get_nearest_node(G, point, method='haversine', return_dist=False)
    nearest =ox.distance.nearest_nodes(G,  point_X,  point_Y, return_dist=False)
    nearest_node = G.nodes[nearest]
    nearest_node["name"] = place["tags"]["name"]
    #nearest_node["osmid"] = place["id"]
    nearest_nodes.append(nearest_node)
#9.5
import pandas as pd
nearest_nodes1=pd.DataFrame(nearest_nodes)
gdf_nodes1=gdf_nodes.reset_index()
nearest_nodes2=pd.merge(nearest_nodes1,gdf_nodes1,on=['y','x'],how='left')
nearest_nodes3=nearest_nodes2[['osmid','y','x','street_count_y','name_y']]
nearest_nodes3.columns = ['osmid','y','x','street_count','name']
nearest_nodes4=nearest_nodes3.to_dict('records')
#10
distance_matrix = []
for source_node in nearest_nodes4:
    distance_row = []
    for target_node in nearest_nodes4:        
        distance = 0;
        if source_node['osmid'] != target_node['osmid']:
            distance = nx.shortest_path_length(G, source_node['osmid'],target_node['osmid'],weight='length', method='dijkstra')
        distance_row.append(distance)
    distance_matrix.append(distance_row)
print(distance_matrix)
#11
def print_solution(manager, routing, assignment):
    """Prints assignment on console."""
    print('距离: {} metre'.format(assignment.ObjectiveValue()))
    index = routing.Start(0)
    plan_output = '遵循的路线:\n'
    route_distance = 0
    while not routing.IsEnd(index):
        plan_output += ' {} ->'.format(manager.IndexToNode(index))
        previous_index = index
        index = assignment.Value(routing.NextVar(index))
        route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
    plan_output += ' {}\n'.format(manager.IndexToNode(index))
    print(plan_output)
#12
def get_solution_route(manager, routing, assignment):
    solution = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        solution.append(manager.IndexToNode(index))
        index = assignment.Value(routing.NextVar(index))
    return solution
#13
def get_route_color(index):
    colors = ['#BF360C','#D84315','#E64A19','#F4511E','#FF5722','#FF7043','#FF8A65','#FFAB91']
    return colors[index%len(colors)]
#14
def get_icon_color(index):
    colors = ['darkred','red','lightred','pink','cadetblue','darkblue','blue','lightblue']
    return colors[index%len(colors)]
#15
# 为 ORTools 准备数据
data = {}
data['distance_matrix'] = distance_matrix
data['num_vehicles'] = 1
data['depot'] = 1
#16
# Create the routing index manager.
manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                           data['num_vehicles'], data['depot'])
#17
# Create Routing Model.
routing = pywrapcp.RoutingModel(manager)


def distance_callback(from_index, to_index):
    """Returns the distance between the two nodes."""
    # Convert from routing variable Index to distance matrix NodeIndex.
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return data['distance_matrix'][from_node][to_node]

transit_callback_index = routing.RegisterTransitCallback(distance_callback)
#18
# Define cost of each arc.
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
#19
# Setting first solution heuristic.
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
#20
# Solve the problem.
assignment = routing.SolveWithParameters(search_parameters)


if assignment:
    print_solution(manager, routing, assignment)
    solution_route = get_solution_route(manager, routing, assignment);
    print(solution_route)
    
    counter = 0
    for index in solution_route:
        popup_title = '<h3><strong>'+str(counter)+'.</strong> '+nearest_nodes[index]["name"]+'</h3>'
        tooltip = popup_title
        
        folium.Marker([nearest_nodes[index]["y"], nearest_nodes[index]["x"]], popup=popup_title,tooltip=tooltip,icon=folium.Icon(color=get_icon_color(index))).add_to(m)        
        counter += 1
        
    counter = 0
    while counter < len(solution_route)-1:
        source_index = solution_route[counter];
        target_index = solution_route[counter+1];
        route = nx.shortest_path(G, nearest_nodes4[source_index]['osmid'],nearest_nodes4[target_index]['osmid'])        
        m = ox.plot_route_folium(G, route, route_map=m, popup_attribute='length',fit_bounds=True,route_color=get_route_color(counter))        
        counter+=1
    m.save(r'Documents/route_planner/results/result.html')
    print("地图已创建,另存为result.html。")
#21
import folium
from IPython.display import display
LDN_COORDINATES = (22.5429,114.0591)
display(m)
