import osmnx as ox
G=ox.graph.graph_from_bbox(north=22.5778, south=22.5038, east=114.1000, west=113.9977)
#ox.plot_graph(G,figsize=(100,100))

#gdf_nodes, gdf_edges = ox.graph_to_gdfs(G)

#ox.save_graph_shapefile(G, filepath=r"Documents/bysj/results/mynetwork.shp")


orig = ox.distance.nearest_nodes(G, X=114.01759, Y=22.53652)
dest = ox.distance.nearest_nodes(G, X=114.08723, Y=22.55193)

speeds = { 'motorway' : 80,
           'trunk' : 80,
           'primary' : 70,
           'secondary' : 50,
           'motorway_link' : 50,
           'trunk_link' : 50,
           'primary_link' : 50,
           'secondary_link' : 50,
            'residential': 35,
            'tertiary': 60
           }
G = ox.speed.add_edge_speeds(G,hwy_speeds=speeds,fallback=50)

G = ox.speed.add_edge_travel_times(G)
route = ox.shortest_path(G, orig, dest, weight="travel_time")

edge_lengths = ox.utils_graph.get_route_edge_attributes(G, route, "length")

sum_length = round(sum(edge_lengths))
orig_x = G.nodes[orig]["x"]
orig_y = G.nodes[orig]["y"]
dest_x = G.nodes[dest]["x"]
dest_y = G.nodes[dest]["y"]
direct_length = round(ox.distance.great_circle_vec(orig_y, orig_x, dest_y, dest_x))

fig, ax = ox.plot_graph_route(G, route, node_size=0,figsize=(100,100))
