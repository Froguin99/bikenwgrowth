
# GRAPH PLOTTING

def holepatchlist_from_cov(cov, map_center):
    """Get a patchlist of holes (= shapely interiors) from a coverage Polygon or MultiPolygon
    """
    holeseq_per_poly = get_holes(cov)
    holepatchlist = []
    for hole_per_poly in holeseq_per_poly:
        for hole in hole_per_poly:
            holepatchlist.append(hole_to_patch(hole, map_center))
    return holepatchlist

def fill_holes(cov):
    """Fill holes (= shapely interiors) from a coverage Polygon or MultiPolygon
    """
    holeseq_per_poly = get_holes(cov)
    holes = []
    for hole_per_poly in holeseq_per_poly:
        for hole in hole_per_poly:
            holes.append(hole)
    eps = 0.00000001
    if isinstance(cov, shapely.geometry.multipolygon.MultiPolygon):
        cov_filled = ops.unary_union([poly for poly in cov] + [Polygon(hole).buffer(eps) for hole in holes])
    elif isinstance(cov, shapely.geometry.polygon.Polygon) and not cov.is_empty:
        cov_filled = ops.unary_union([cov] + [Polygon(hole).buffer(eps) for hole in holes])
    return cov_filled

def extract_relevant_polygon(placeid, mp):
    """Return the most relevant polygon of a multipolygon mp, for being considered the city limit.
    Depends on location.
    """
    if isinstance(mp, shapely.geometry.polygon.Polygon):
        return mp
    if placeid == "tokyo": # If Tokyo, take poly with most northern bound, otherwise largest
        p = max(mp, key=lambda a: a.bounds[-1])
    else:
        p = max(mp, key=lambda a: a.area)
    return p

def get_holes(cov):
    """Get holes (= shapely interiors) from a coverage Polygon or MultiPolygon
    """
    holes = []
    if isinstance(cov, shapely.geometry.multipolygon.MultiPolygon):
        for pol in cov.geoms: # cov is generally a MultiPolygon, so we iterate through its Polygons
            holes.append(pol.interiors)
    elif isinstance(cov, shapely.geometry.polygon.Polygon) and not cov.is_empty:
        holes.append(cov.interiors)
    return holes

def cov_to_patchlist(cov, map_center, return_holes = True):
    """Turns a coverage Polygon or MultiPolygon into a matplotlib patch list, for plotting
    """
    p = []
    if isinstance(cov, shapely.geometry.multipolygon.MultiPolygon):
        for pol in cov.geoms: # cov is generally a MultiPolygon, so we iterate through its Polygons
            p.append(pol_to_patch(pol, map_center))
    elif isinstance(cov, shapely.geometry.polygon.Polygon) and not cov.is_empty:
        p.append(pol_to_patch(cov, map_center))
    if not return_holes:
        return p
    else:
        holepatchlist = holepatchlist_from_cov(cov, map_center)
        return p, holepatchlist

def pol_to_patch(pol, map_center):
    """Turns a coverage Polygon into a matplotlib patch, for plotting
    """
    y, x = pol.exterior.coords.xy
    pos_transformed, _ = project_pos(y, x, map_center)
    return matplotlib.patches.Polygon(pos_transformed)

def hole_to_patch(hole, map_center):
    """Turns a LinearRing (hole) into a matplotlib patch, for plotting
    """
    y, x = hole.coords.xy
    pos_transformed, _ = project_pos(y, x, map_center)
    return matplotlib.patches.Polygon(pos_transformed)


def set_analysissubplot(key):
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1])
    if key in ["length", "length_lcc", "coverage", "poi_coverage", "components", "efficiency_local", "efficiency_global"]:
        ax.set_ylim(bottom = 0)
    if key in ["directness_lcc", "directness_lcc_linkwise", "directness", "directness_all_linkwise"]:
        ax.set_ylim(bottom = 0.2)
    if key in ["directness_lcc", "directness_lcc_linkwise", "directness", "directness_all_linkwise", "efficiency_global", "efficiency_local"]:
        ax.set_ylim(top = 1)


def initplot():
    fig = plt.figure(figsize=(plotparam["bbox"][0]/plotparam["dpi"], plotparam["bbox"][1]/plotparam["dpi"]), dpi=plotparam["dpi"])
    plt.axes().set_aspect('equal')
    plt.axes().set_xmargin(0.01)
    plt.axes().set_ymargin(0.01)
    plt.axes().set_axis_off() # Does not work anymore - unnown why not.
    return fig

def nodesize_from_pois(nnids):
    """Determine POI node size based on number of POIs.
    The more POIs the smaller (linearly) to avoid overlaps.
    """
    minnodesize = 30
    maxnodesize = 220
    return max(minnodesize, maxnodesize-len(nnids))


def simplify_ig(G):
    """Simplify an igraph with ox.simplify_graph
    """
    G_temp = copy.deepcopy(G)
    G_temp.es["length"] = G_temp.es["weight"]
    output = ig.Graph.from_networkx(ox.simplify_graph(nx.MultiDiGraph(G_temp.to_networkx())).to_undirected())
    output.es["weight"] = output.es["length"]
    return output


def nxdraw(G, networktype, map_center = False, nnids = False, drawfunc = "nx.draw", nodesize = 0, weighted = False, maxwidthsquared = 0, simplified = False):
    """Take an igraph graph G and draw it with a networkx drawfunc.
    """
    if simplified:
        G.es["length"] = G.es["weight"]
        G_nx = ox.simplify_graph(nx.MultiDiGraph(G.to_networkx())).to_undirected()
    else:
        G_nx = G.to_networkx()
    if nnids is not False: # Restrict to nnids node ids
        nnids_nx = [k for k,v in dict(G_nx.nodes(data=True)).items() if v['id'] in nnids]
        G_nx = G_nx.subgraph(nnids_nx)
        
    pos_transformed, map_center = project_nxpos(G_nx, map_center)
    if weighted is True:
        # The max width should be the node diameter (=sqrt(nodesize))
        widths = list(nx.get_edge_attributes(G_nx, "weight").values())
        widthfactor = 1.1 * math.sqrt(maxwidthsquared) / max(widths)
        widths = [max(0.33, w * widthfactor) for w in widths]
        eval(drawfunc)(G_nx, pos_transformed, **plotparam[networktype], node_size = nodesize, width = widths)
    elif type(weighted) is float or type(weighted) is int and weighted > 0:
        eval(drawfunc)(G_nx, pos_transformed, **plotparam[networktype], node_size = nodesize, width = weighted)
    else:
        eval(drawfunc)(G_nx, pos_transformed, **plotparam[networktype], node_size = nodesize)
    return map_center



# OTHER FUNCTIONS

def common_entries(*dcts):
    """Like zip() but for dicts.
    See: https://stackoverflow.com/questions/16458340/python-equivalent-of-zip-for-dictionaries
    """
    if not dcts:
        return
    for i in set(dcts[0]).intersection(*dcts[1:]):
        yield (i,) + tuple(d[i] for d in dcts)

def project_nxpos(G, map_center = False):
    """Take a spatial nx network G and projects its GPS coordinates to local azimuthal.
    Returns transformed positions, as used by nx.draw()
    """
    lats = nx.get_node_attributes(G, 'x')
    lons = nx.get_node_attributes(G, 'y')
    pos = {nid:(lat,-lon) for (nid,lat,lon) in common_entries(lats,lons)}
    if map_center:
        loncenter = map_center[0]
        latcenter = map_center[1]
    else:
        loncenter = np.mean(list(lats.values()))
        latcenter = -1* np.mean(list(lons.values()))
    local_azimuthal_projection = "+proj=aeqd +R=6371000 +units=m +lat_0={} +lon_0={}".format(latcenter, loncenter)
    # Use transformer: https://gis.stackexchange.com/questions/127427/transforming-shapely-polygon-and-multipolygon-objects
    wgs84_to_aeqd = pyproj.Transformer.from_proj(
        pyproj.Proj("+proj=longlat +datum=WGS84 +no_defs"),
        pyproj.Proj(local_azimuthal_projection))
    pos_transformed = {nid:list(ops.transform(wgs84_to_aeqd.transform, Point(latlon)).coords)[0] for nid, latlon in pos.items()}
    return pos_transformed, (loncenter,latcenter)


def project_pos(lats, lons, map_center = False):
    """Project GPS coordinates to local azimuthal.
    """
    pos = [(lat,-lon) for lat,lon in zip(lats,lons)]
    if map_center:
        loncenter = map_center[0]
        latcenter = map_center[1]
    else:
        loncenter = np.mean(list(lats.values()))
        latcenter = -1* np.mean(list(lons.values()))
    local_azimuthal_projection = "+proj=aeqd +R=6371000 +units=m +lat_0={} +lon_0={}".format(latcenter, loncenter)
    # Use transformer: https://gis.stackexchange.com/questions/127427/transforming-shapely-polygon-and-multipolygon-objects
    wgs84_to_aeqd = pyproj.Transformer.from_proj(
        pyproj.Proj("+proj=longlat +datum=WGS84 +no_defs"),
        pyproj.Proj(local_azimuthal_projection))
    pos_transformed = [(ops.transform(wgs84_to_aeqd.transform, Point(latlon)).coords)[0] for latlon in pos]
    return pos_transformed, (loncenter,latcenter)


def round_coordinates(G, r = 7):
    for v in G.vs:
        G.vs[v.index]["x"] = round(G.vs[v.index]["x"], r)
        G.vs[v.index]["y"] = round(G.vs[v.index]["y"], r)

def mirror_y(G):
    for v in G.vs:
        y = G.vs[v.index]["y"]
        G.vs[v.index]["y"] = -y
    
def dist(v1, v2):
    dist = haversine((v1['y'],v1['x']),(v2['y'],v2['x']), unit="m") # x is lon, y is lat
    return dist

def dist_vector(v1_list, v2_list):
    dist_list = haversine_vector(v1_list, v2_list, unit="m") # [(lat,lon)], [(lat,lon)]
    return dist_list

def osm_to_ig(node, edge, weighting):
    """ Turns a node and edge dataframe into an igraph Graph.
    """
    G = ig.Graph(directed=False)
    x_coords = node['x'].tolist() 
    y_coords = node['y'].tolist()
    ids = node['osmid'].tolist()
    coords = []

    for i in range(len(x_coords)):
        G.add_vertex(x=x_coords[i], y=y_coords[i], id=ids[i])
        coords.append((x_coords[i], y_coords[i]))

    id_dict = dict(zip(G.vs['id'], np.arange(0, G.vcount()).tolist()))
    coords_dict = dict(zip(np.arange(0, G.vcount()).tolist(), coords))

    edge_list = []
    edge_info = {
        "weight": [],
        "osmid": [],
        # Only include ori_length if weighting is True
        "ori_length": [] if weighting else None  
    }
    
    for i in range(len(edge)):
        edge_list.append([id_dict.get(edge['u'][i]), id_dict.get(edge['v'][i])])
        edge_info["weight"].append(round(edge['length'][i], 10))
        edge_info["osmid"].append(edge['osmid'][i])
        
        if weighting:  # Only add ori_length if weighting is True
            edge_info["ori_length"].append(edge['ori_length'][i])  # Store the original length

    G.add_edges(edge_list)  # Add edges without attributes
    for i in range(len(edge)):
        G.es[i]["weight"] = edge_info["weight"][i]
        G.es[i]["osmid"] = edge_info["osmid"][i]
        
        if weighting:  # Set the original length only if weighting is True
            G.es[i]["ori_length"] = edge_info["ori_length"][i]

    G.simplify(combine_edges=max)
    return G


## Old 
# def osm_to_ig(node, edge, weighting=None):
#     """ Turns a node and edge dataframe into an igraph Graph. """
    
#     G = ig.Graph(directed=False)

#     # Print first few rows of edge dataframe
#     print("First 5 edges with lengths and maxspeeds:")
#     print(edge[['u', 'v', 'length', 'maxspeed']].head())

#     x_coords = node['x'].tolist() 
#     y_coords = node['y'].tolist()
#     ids = node['osmid'].tolist()
#     coords = []

#     for i in range(len(x_coords)):
#         G.add_vertex(x=x_coords[i], y=y_coords[i], id=ids[i])
#         coords.append((x_coords[i], y_coords[i]))

#     id_dict = dict(zip(G.vs['id'], np.arange(0, G.vcount()).tolist()))
#     coords_dict = dict(zip(np.arange(0, G.vcount()).tolist(), coords))

#     edge_list = []
#     edge_info = {"weight": [], "osmid": []}

#     if weighting:
#         print("Applying weighted calculation to edges.")
#         for i in range(len(edge)):
#             u, v = edge['u'][i], edge['v'][i]
#             edge_list.append([id_dict.get(u), id_dict.get(v)])
#             length = edge['length'][i]

#             try:
#                 speed_limit = int(str(edge['maxspeed'][i]).split()[0]) if pd.notnull(edge['maxspeed'][i]) else 30
#             except (ValueError, IndexError):
#                 speed_limit = 30

#             weight = (length * (speed_limit / 10)) * 10000
#             edge_info["weight"].append(round(weight, 10))
#             edge_info["osmid"].append(edge['osmid'][i])
#     else:
#         print("Applying unweighted calculation to edges.")
#         for i in range(len(edge)):
#             edge_list.append([id_dict.get(edge['u'][i]), id_dict.get(edge['v'][i])])
#             edge_info["weight"].append(round(edge['length'][i], 10))
#             edge_info["osmid"].append(edge['osmid'][i])

#     # Debug: Print edge list
#     #print("Edge list:", edge_list)

#     G.add_edges(edge_list)
    
#     # Check that the edge count matches
#     print(f"Number of edges in edge_list: {len(edge_list)}, edges in graph: {G.ecount()}")

#     for i in range(len(edge_list)):
#         G.es[i]["weight"] = edge_info["weight"][i]
#         G.es[i]["osmid"] = edge_info["osmid"][i]

#     # Debug: Print final edge weights
#     print("Final edge weights after assignment:")
#     print(G.es["weight"][:5])  # Check first few for validation

#     G.simplify(combine_edges=max)

#     # Assuming edges is a DataFrame or a list of your edges
#     for index, edge in enumerate(edges.itertuples()):
#         length = edge.length
#         speed_limit = edge.maxspeed
#         weight = length * (3600 / speed_limit)  # Calculate the weight based on length and speed

#         # Print only the first 15 edges
#         if index < 15:
#             print(f"Edge ID: {index}, Length: {length}, Speed limit: {speed_limit}, Calculated weight: {weight}")
#         # Add the weight to the graph here

#     return G



def compress_file(p, f, filetype = ".csv", delete_uncompressed = True):
    with zipfile.ZipFile(p + f + ".zip", 'w', zipfile.ZIP_DEFLATED) as zfile:
        zfile.write(p + f + filetype, f + filetype)
    if delete_uncompressed: os.remove(p + f + filetype)

def ox_to_csv(G, p, placeid, parameterid, postfix = "", compress = True, verbose = True):
    if "crs" not in G.graph:
        G.graph["crs"] = 'epsg:4326' # needed for OSMNX's graph_to_gdfs in utils_graph.py
    try:
        node, edge = ox.graph_to_gdfs(G)
    except ValueError:
        node, edge = gpd.GeoDataFrame(), gpd.GeoDataFrame()
    prefix = placeid + '_' + parameterid + postfix

    node.to_csv(p + prefix + '_nodes.csv', index = True)
    if compress: compress_file(p, prefix + '_nodes')
 
    edge.to_csv(p + prefix + '_edges.csv', index = True)
    if compress: compress_file(p, prefix + '_edges')

    if verbose: print(placeid + ": Successfully wrote graph " + parameterid + postfix)

def check_extract_zip(p, prefix):
    """ Check if a zip file prefix+'_nodes.zip' and + prefix+'_edges.zip'
    is available at path p. If so extract it and return True, otherwise False.
    If you call this function, remember to clean up (i.e. delete the unzipped files)
    after you are done like this:

    if compress:
        os.remove(p + prefix + '_nodes.csv')
        os.remove(p + prefix + '_edges.csv')
    """

    try: # Use zip files if available
        with zipfile.ZipFile(p + prefix + '_nodes.zip', 'r') as zfile:
            zfile.extract(prefix + '_nodes.csv', p)
        with zipfile.ZipFile(p + prefix + '_edges.zip', 'r') as zfile:
            zfile.extract(prefix + '_edges.csv', p)
        return True
    except:
        return False


def csv_to_ox(p, placeid, parameterid):
    """ Load a networkx graph from _edges.csv and _nodes.csv
    The edge file must have attributes u,v,osmid,length
    The node file must have attributes y,x,osmid
    Only these attributes are loaded.
    """
    prefix = placeid + '_' + parameterid
    compress = check_extract_zip(p, prefix)
    
    with open(p + prefix + '_edges.csv', 'r') as f:
        header = f.readline().strip().split(",")

        lines = []
        for line in csv.reader(f, quotechar='"', delimiter=',', quoting=csv.QUOTE_ALL, skipinitialspace=True):
            line_list = [c for c in line]
            osmid = str(eval(line_list[header.index("osmid")])[0]) if isinstance(eval(line_list[header.index("osmid")]), list) else line_list[header.index("osmid")] # If this is a list due to multiedges, just load the first osmid
            length = str(eval(line_list[header.index("length")])[0]) if isinstance(eval(line_list[header.index("length")]), list) else line_list[header.index("length")] # If this is a list due to multiedges, just load the first osmid
            line_string = "" + line_list[header.index("u")] + " "+ line_list[header.index("v")] + " " + osmid + " " + length
            lines.append(line_string)
        G = nx.parse_edgelist(lines, nodetype = int, data = (("osmid", int),("length", float)), create_using = nx.MultiDiGraph) # MultiDiGraph is necessary for OSMNX, for example for get_undirected(G) in utils_graph.py
    with open(p + prefix + '_nodes.csv', 'r') as f:
        header = f.readline().strip().split(",")
        values_x = {}
        values_y = {}
        for line in csv.reader(f, quotechar='"', delimiter=',', quoting=csv.QUOTE_ALL, skipinitialspace=True):
            line_list = [c for c in line]
            osmid = int(line_list[header.index("osmid")])
            values_x[osmid] = float(line_list[header.index("x")])
            values_y[osmid] = float(line_list[header.index("y")])

        nx.set_node_attributes(G, values_x, "x")
        nx.set_node_attributes(G, values_y, "y")

    if compress:
        os.remove(p + prefix + '_nodes.csv')
        os.remove(p + prefix + '_edges.csv')
    return G

def calculate_weight(row):
    """
    Calculate new weight based on length and speed limit.
    """
    # Default speed limit is 30 mph if 'maxspeed' is missing or NaN
    if pd.isna(row['maxspeed']):
        speed_factor = 3  # Corresponding to 30 mph
    else:
        speed_factor = int(str(row['maxspeed']).split()[0][0])  # Extract first digit from the speed. 
        # This presumes no speed limit over 99, which is reasonable for most roads.
        # however this could produce issues in some countries with speed limits over 100 km/h?
    
    # Multiply the speed factor by the length to get the new weight
    return row['length'] * speed_factor

def csv_to_ig(p, placeid, parameterid, cleanup=True, weighting=None):
    """ Load an ig graph from _edges.csv and _nodes.csv
    The edge file must have attributes u,v,osmid,length
    The node file must have attributes y,x,osmid
    Only these attributes are loaded.
    """
    prefix = placeid + '_' + parameterid
    compress = check_extract_zip(p, prefix)
    empty = False
    try:
        n = pd.read_csv(p + prefix + '_nodes.csv')
        e = pd.read_csv(p + prefix + '_edges.csv')
    except:
        empty = True

    if compress and cleanup and not SERVER:  # Do not clean up on the server as csv is needed in parallel jobs
        os.remove(p + prefix + '_nodes.csv')
        os.remove(p + prefix + '_edges.csv')

    if empty:
        return ig.Graph(directed=False)

    if weighting:
        # Process the edges to modify length based on speed limits
        e['maxspeed'] = e['maxspeed'].str.replace(' mph', '', regex=False).astype(float)
        e['maxspeed'].fillna(20, inplace=True)  # Assign default speed of 20 where NaN
        e['ori_length'] = e['length']  # Store original length only if weighting is True
        e['length'] = e['length'] * e['maxspeed']  # Modify the length based on speed

    G = osm_to_ig(n, e, weighting)  # Pass weighting to osm_to_ig
    round_coordinates(G)
    mirror_y(G)
    return G



def ig_to_geojson(G):
    linestring_list = []
    for e in G.es():
        linestring_list.append(geojson.LineString([(e.source_vertex["x"], -e.source_vertex["y"]), (e.target_vertex["x"], -e.target_vertex["y"])]))
    G_geojson = geojson.GeometryCollection(linestring_list)
    return G_geojson




# NETWORK GENERATION

def highest_closeness_node(G):
    closeness_values = G.closeness(weights = 'weight')
    sorted_closeness = sorted(closeness_values, reverse = True)
    index = closeness_values.index(sorted_closeness[0])
    return G.vs(index)['id']

def clusterindices_by_length(clusterinfo, rev = True):
    return [k for k, v in sorted(clusterinfo.items(), key=lambda item: item[1]["length"], reverse = rev)]

class MyPoint:
    def __init__(self,x,y):
        self.x = x
        self.y = y
        
def ccw(A,B,C):
    return (C.y-A.y) * (B.x-A.x) > (B.y-A.y) * (C.x-A.x)

def segments_intersect(A,B,C,D):
    """Check if two line segments intersect (except for colinearity)
    Returns true if line segments AB and CD intersect properly.
    Adapted from: https://stackoverflow.com/questions/3838329/how-can-i-check-if-two-segments-intersect
    """
    if (A.x == C.x and A.y == C.y) or (A.x == D.x and A.y == D.y) or (B.x == C.x and B.y == C.y) or (B.x == D.x and B.y == D.y): return False # If the segments share an endpoint they do not intersect properly
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

def new_edge_intersects(G, enew):
    """Given a graph G and a potential new edge enew,
    check if enew will intersect any old edge.
    """
    E1 = MyPoint(enew[0], enew[1])
    E2 = MyPoint(enew[2], enew[3])
    for e in G.es():
        O1 = MyPoint(e.source_vertex["x"], e.source_vertex["y"])
        O2 = MyPoint(e.target_vertex["x"], e.target_vertex["y"])
        if segments_intersect(E1, E2, O1, O2):
            return True
    return False
    

def delete_overlaps(G_res, G_orig, verbose = False):
    """Deletes inplace all overlaps of G_res with G_orig (from G_res)
    based on node ids. In other words: G_res -= G_orig
    """
    del_edges = []
    for e in list(G_res.es):
        try:
            n1_id = e.source_vertex["id"]
            n2_id = e.target_vertex["id"]
            # If there is already an edge in the original network, delete it
            n1_index = G_orig.vs.find(id = n1_id).index
            n2_index = G_orig.vs.find(id = n2_id).index
            if G_orig.are_connected(n1_index, n2_index):
                del_edges.append(e.index)
        except:
            pass
    G_res.delete_edges(del_edges)
    # Remove isolated nodes
    isolated_nodes = G_res.vs.select(_degree_eq=0)
    G_res.delete_vertices(isolated_nodes)
    if verbose: print("Removed " + str(len(del_edges)) + " overlapping edges and " + str(len(isolated_nodes)) + " nodes.")

def constrict_overlaps(G_res, G_orig, factor = 5):
    """Increases length by factor of all overlaps of G_res with G_orig (in G_res) based on edge ids.
    """
    for e in list(G_res.es):
        try:
            n1_id = e.source_vertex["id"]
            n2_id = e.target_vertex["id"]
            n1_index = G_orig.vs.find(id = n1_id).index
            n2_index = G_orig.vs.find(id = n2_id).index
            if G_orig.are_connected(n1_index, n2_index):
                G_res.es[e.index]["weight"] = factor * G_res.es[e.index]["weight"]
        except:
            pass



    

def greedy_triangulation_routing_clusters(G, G_total, clusters, clusterinfo, prune_quantiles = [1], prune_measure = "betweenness", verbose = False, full_run = False):
    """Greedy Triangulation (GT) of a bike network G's clusters,
    then routing on the graph G_total that includes car infra to connect the GT.
    G and G_total are ipgraph graphs
    
    The GT connects pairs of clusters in ascending order of their distance provided
    that no edge crossing is introduced. It leads to a maximal connected planar
    graph, while minimizing the total length of edges considered. 
    See: cardillo2006spp
    
    Distance here is routing distance, while edge crossing is checked on an abstract 
    level.
    """
    
    if len(clusters) < 2: return ([], []) # We can't do anything with less than 2 clusters

    centroid_indices = [v["centroid_index"] for k, v in sorted(clusterinfo.items(), key=lambda item: item[1]["size"], reverse = True)]
    G_temp = copy.deepcopy(G_total)
    for e in G_temp.es: # delete all edges
        G_temp.es.delete(e)
    
    clusterpairs = clusterpairs_by_distance(G, G_total, clusters, clusterinfo, True, verbose, full_run)
    if len(clusterpairs) == 0: return ([], [])
    
    centroidpairs = [((clusterinfo[c[0][0]]['centroid_id'], clusterinfo[c[0][1]]['centroid_id']), c[2]) for c in clusterpairs]
    
    GT_abstracts = []
    GTs = []
    for prune_quantile in prune_quantiles:
        GT_abstract = copy.deepcopy(G_temp.subgraph(centroid_indices))
        GT_abstract = greedy_triangulation(GT_abstract, centroidpairs, prune_quantile, prune_measure)
        GT_abstracts.append(GT_abstract)

        centroidids_closestnodeids = {} # dict for retrieveing quickly closest node ids pairs from centroidid pairs
        for x in clusterpairs:
            centroidids_closestnodeids[(clusterinfo[x[0][0]]["centroid_id"], clusterinfo[x[0][1]]["centroid_id"])] = (x[1][0], x[1][1])
            centroidids_closestnodeids[(clusterinfo[x[0][1]]["centroid_id"], clusterinfo[x[0][0]]["centroid_id"])] = (x[1][1], x[1][0]) # also add switched version as we do not care about order

        # Get node pairs we need to route, sorted by distance
        routenodepairs = []
        for e in GT_abstract.es:
            # get the centroid-ids from closestnode-ids
            routenodepairs.append([centroidids_closestnodeids[(e.source_vertex["id"], e.target_vertex["id"])], e["weight"]])

        routenodepairs.sort(key=lambda x: x[1])

        # Do the routing, on G_total
        GT_indices = set()
        for poipair, poipair_distance in routenodepairs:
            poipair_ind = (G_total.vs.find(id = poipair[0]).index, G_total.vs.find(id = poipair[1]).index)
            sp = set(G_total.get_shortest_paths(poipair_ind[0], poipair_ind[1], weights = "weight", output = "vpath")[0])
            GT_indices = GT_indices.union(sp)

        GT = G_total.induced_subgraph(GT_indices)
        GTs.append(GT)
    
    return(GTs, GT_abstracts)


def clusterpairs_by_distance(G, G_total, clusters, clusterinfo, return_distances = False, verbose = False, full_run = False):
    """Calculates the (weighted) graph distances on G for a number of clusters.
    Returns all pairs of cluster ids and closest nodes in ascending order of their distance. 
    If return_distances, then distances are also returned.

    Returns a list containing these elements, sorted by distance:
    [(clusterid1, clusterid2), (closestnodeid1, closestnodeid2), distance]
    """
    
    cluster_indices = clusterindices_by_length(clusterinfo, False) # Start with the smallest so the for loop is as short as possible
    clusterpairs = []
    clustercopies = {}
    
    # Create copies of all clusters
    for i in range(len(cluster_indices)):
        clustercopies[i] = clusters[i].copy()
        
    # Take one cluster
    for i, c1 in enumerate(cluster_indices[:-1]):
        c1_indices = G_total.vs.select(lambda x: x["id"] in clustercopies[c1].vs()["id"]).indices
        print("Working on cluster " + str(i+1) + " of " + str(len(cluster_indices)) + "...")
        for j, c2 in enumerate(cluster_indices[i+1:]):
            closest_pair = {'i': -1, 'j': -1}
            min_dist = np.inf
            c2_indices = G_total.vs.select(lambda x: x["id"] in clustercopies[c2].vs()["id"]).indices
            if verbose: print("... routing " + str(len(c1_indices)) + " nodes to " + str(len(c2_indices)) + " nodes in other cluster " + str(j+1) + " of " + str(len(cluster_indices[i+1:])) + ".")
            
            if full_run:
                # Compare all pairs of nodes in both clusters (takes long)
                for a in list(c1_indices):
                    sp = G_total.get_shortest_paths(a, c2_indices, weights = "weight", output = "epath")

                    if all([not elem for elem in sp]):
                        # If there is no path from one node, there is no path from any node
                        break
                    else:
                        for path, c2_index in zip(sp, c2_indices):
                            if len(path) >= 1:
                                dist_nodes = sum([G_total.es[e]['weight'] for e in path])
                                if dist_nodes < min_dist:
                                    closest_pair['i'] = G_total.vs[a]["id"]
                                    closest_pair['j'] = G_total.vs[c2_index]["id"]
                                    min_dist = dist_nodes
            else:
                # Do a heuristic that should be close enough.
                # From cluster 1, look at all shortest paths only from its centroid
                a = clusterinfo[c1]["centroid_index"]
                sp = G_total.get_shortest_paths(a, c2_indices, weights = "weight", output = "epath")
                if all([not elem for elem in sp]):
                    # If there is no path from one node, there is no path from any node
                    break
                else:
                    for path, c2_index in zip(sp, c2_indices):
                        if len(path) >= 1:
                            dist_nodes = sum([G_total.es[e]['weight'] for e in path])
                            if dist_nodes < min_dist:
                                closest_pair['j'] = G_total.vs[c2_index]["id"]
                                min_dist = dist_nodes
                # Closest c2 node to centroid1 found. Now find all c1 nodes to that closest c2 node.
                b = G_total.vs.find(id = closest_pair['j']).index
                sp = G_total.get_shortest_paths(b, c1_indices, weights = "weight", output = "epath")
                if all([not elem for elem in sp]):
                    # If there is no path from one node, there is no path from any node
                    break
                else:
                    for path, c1_index in zip(sp, c1_indices):
                        if len(path) >= 1:
                            dist_nodes = sum([G_total.es[e]['weight'] for e in path])
                            if dist_nodes <= min_dist: # <=, not <!
                                closest_pair['i'] = G_total.vs[c1_index]["id"]
                                min_dist = dist_nodes
            
            if closest_pair['i'] != -1 and closest_pair['j'] != -1:
                clusterpairs.append([(c1, c2), (closest_pair['i'], closest_pair['j']), min_dist])
                                    
    clusterpairs.sort(key = lambda x: x[-1])
    if return_distances:
        return clusterpairs
    else:
        return [[o[0], o[1]] for o in clusterpairs]


def mst_routing(G, pois, weighting=None):
    """Minimum Spanning Tree (MST) of a graph G's node subset pois,
    then routing to connect the MST.
    G is an ipgraph graph, pois is a list of node ids.
    
    The MST is the planar graph with the minimum number of (weighted) 
    links in order to assure connectedness.

    Distance here is routing distance, while edge crossing is checked on an abstract 
    level.
    """

    if len(pois) < 2: return (ig.Graph(), ig.Graph()) # We can't do anything with less than 2 POIs

    # MST_abstract is the MST with same nodes but euclidian links
    pois_indices = set()
    for poi in pois:
        pois_indices.add(G.vs.find(id = poi).index)
    G_temp = copy.deepcopy(G)
    for e in G_temp.es: # delete all edges
        G_temp.es.delete(e)
        
    poipairs = poipairs_by_distance(G, pois, weighting, True)
    if len(poipairs) == 0: return (ig.Graph(), ig.Graph())

    MST_abstract = copy.deepcopy(G_temp.subgraph(pois_indices))
    for poipair, poipair_distance in poipairs:
        poipair_ind = (MST_abstract.vs.find(id = poipair[0]).index, MST_abstract.vs.find(id = poipair[1]).index)
        MST_abstract.add_edge(poipair_ind[0], poipair_ind[1] , weight = poipair_distance)
    MST_abstract = MST_abstract.spanning_tree(weights = "weight")

    # Get node pairs we need to route, sorted by distance
    routenodepairs = {}
    for e in MST_abstract.es:
        routenodepairs[(e.source_vertex["id"], e.target_vertex["id"])] = e["weight"]
    routenodepairs = sorted(routenodepairs.items(), key = lambda x: x[1])

    # Do the routing
    MST_indices = set()
    for poipair, poipair_distance in routenodepairs:
        poipair_ind = (G.vs.find(id = poipair[0]).index, G.vs.find(id = poipair[1]).index)
        sp = set(G.get_shortest_paths(poipair_ind[0], poipair_ind[1], weights = "weight", output = "vpath")[0])
        MST_indices = MST_indices.union(sp)

    MST = G.induced_subgraph(MST_indices)
    
    return (MST, MST_abstract)



def greedy_triangulation(GT, poipairs, prune_quantile = 1, prune_measure = "betweenness", edgeorder = False):
    """Greedy Triangulation (GT) of a graph GT with an empty edge set.
    Distances between pairs of nodes are given by poipairs.
    
    The GT connects pairs of nodes in ascending order of their distance provided
    that no edge crossing is introduced. It leads to a maximal connected planar
    graph, while minimizing the total length of edges considered. 
    See: cardillo2006spp
    """
    
    for poipair, poipair_distance in poipairs:
        poipair_ind = (GT.vs.find(id = poipair[0]).index, GT.vs.find(id = poipair[1]).index)
        if not new_edge_intersects(GT, (GT.vs[poipair_ind[0]]["x"], GT.vs[poipair_ind[0]]["y"], GT.vs[poipair_ind[1]]["x"], GT.vs[poipair_ind[1]]["y"])):
            GT.add_edge(poipair_ind[0], poipair_ind[1], weight = poipair_distance)
            
    # Get the measure for pruning
    if prune_measure == "betweenness":
        BW = GT.edge_betweenness(directed = False, weights = "weight")
        qt = np.quantile(BW, 1-prune_quantile)
        sub_edges = []
        for c, e in enumerate(GT.es):
            if BW[c] >= qt: 
                sub_edges.append(c)
            GT.es[c]["bw"] = BW[c]
            GT.es[c]["width"] = math.sqrt(BW[c]+1)*0.5
        # Prune
        GT = GT.subgraph_edges(sub_edges)
    elif prune_measure == "closeness":
        CC = GT.closeness(vertices = None, weights = "weight")
        qt = np.quantile(CC, 1-prune_quantile)
        sub_nodes = []
        for c, v in enumerate(GT.vs):
            if CC[c] >= qt: 
                sub_nodes.append(c)
            GT.vs[c]["cc"] = CC[c]
        GT = GT.induced_subgraph(sub_nodes)
    elif prune_measure == "random":
        ind = np.quantile(np.arange(len(edgeorder)), prune_quantile, interpolation = "lower") + 1 # "lower" and + 1 so smallest quantile has at least one edge
        GT = GT.subgraph_edges(edgeorder[:ind])
    
    return GT


def restore_original_lengths(G):
    """Restore original lengths from the 'ori_length' attribute."""
    for e in G.es:
        e["weight"] = e["ori_length"]
 


def greedy_triangulation_routing(G, pois, weighting=None, prune_quantiles = [1], prune_measure = "betweenness"):
    """Greedy Triangulation (GT) of a graph G's node subset pois,
    then routing to connect the GT (up to a quantile of betweenness
    betweenness_quantile).
    G is an ipgraph graph, pois is a list of node ids.
    
    The GT connects pairs of nodes in ascending order of their distance provided
    that no edge crossing is introduced. It leads to a maximal connected planar
    graph, while minimizing the total length of edges considered. 
    See: cardillo2006spp
    
    Distance here is routing distance, while edge crossing is checked on an abstract 
    level.
    """
    
    if len(pois) < 2: return ([], []) # We can't do anything with less than 2 POIs

    # GT_abstract is the GT with same nodes but euclidian links to keep track of edge crossings
    pois_indices = set()
    for poi in pois:
        pois_indices.add(G.vs.find(id = poi).index)
    G_temp = copy.deepcopy(G)
    for e in G_temp.es: # delete all edges
        G_temp.es.delete(e)
        
    poipairs = poipairs_by_distance(G, pois, weighting, True)
    if len(poipairs) == 0: return ([], [])

    if prune_measure == "random":
        # run the whole GT first
        GT = copy.deepcopy(G_temp.subgraph(pois_indices))
        for poipair, poipair_distance in poipairs:
            poipair_ind = (GT.vs.find(id = poipair[0]).index, GT.vs.find(id = poipair[1]).index)
            if not new_edge_intersects(GT, (GT.vs[poipair_ind[0]]["x"], GT.vs[poipair_ind[0]]["y"], GT.vs[poipair_ind[1]]["x"], GT.vs[poipair_ind[1]]["y"])):
                GT.add_edge(poipair_ind[0], poipair_ind[1], weight = poipair_distance)
        # create a random order for the edges
        random.seed(0) # const seed for reproducibility
        edgeorder = random.sample(range(GT.ecount()), k = GT.ecount())
    else: 
        edgeorder = False
    
    GT_abstracts = []
    GTs = []
    for prune_quantile in tqdm(prune_quantiles, desc = "Greedy triangulation", leave = False):
        GT_abstract = copy.deepcopy(G_temp.subgraph(pois_indices))
        GT_abstract = greedy_triangulation(GT_abstract, poipairs, prune_quantile, prune_measure, edgeorder)
        GT_abstracts.append(GT_abstract)
        
        # Get node pairs we need to route, sorted by distance
        routenodepairs = {}
        for e in GT_abstract.es:
            routenodepairs[(e.source_vertex["id"], e.target_vertex["id"])] = e["weight"]
        routenodepairs = sorted(routenodepairs.items(), key = lambda x: x[1])

        # Do the routing
        GT_indices = set()
        for poipair, poipair_distance in routenodepairs:
            poipair_ind = (G.vs.find(id = poipair[0]).index, G.vs.find(id = poipair[1]).index)
            # debug
            #print(f"Edge weights before routing: {G.es['weight'][:10]}")  # Prints first 10 weights
            #print(f"Routing between: {poipair[0]} and {poipair[1]} with distance: {poipair_distance}")
            sp = set(G.get_shortest_paths(poipair_ind[0], poipair_ind[1], weights = "weight", output = "vpath")[0])
            #print(f"Shortest path between {poipair[0]} and {poipair[1]}: {sp}")

            GT_indices = GT_indices.union(sp)

        GT = G.induced_subgraph(GT_indices)
        GTs.append(GT)
    
    return (GTs, GT_abstracts)
    
    
def poipairs_by_distance(G, pois, weighting=None, return_distances = False):
    """Calculates the (weighted) graph distances on G for a subset of nodes pois.
    Returns all pairs of poi ids in ascending order of their distance. 
    If return_distances, then distances are also returned.
    If we are using a weighted graph, we need to calculate the distances using orignal
    edge lengths rather than adjusted weighted lengths.
    """
    
    # Get poi indices
    indices = []
    for poi in pois:
        indices.append(G_carall.vs.find(id = poi).index)
    
    # Get sequences of nodes and edges in shortest paths between all pairs of pois
    poi_nodes = []
    poi_edges = []
    for c, v in enumerate(indices):
        poi_nodes.append(G.get_shortest_paths(v, indices[c:], weights = "weight", output = "vpath"))
        poi_edges.append(G.get_shortest_paths(v, indices[c:], weights = "weight", output = "epath"))

    # Sum up weights (distances) of all paths
    poi_dist = {}
    for paths_n, paths_e in zip(poi_nodes, poi_edges):
        for path_n, path_e in zip(paths_n, paths_e):
            # Sum up distances of path segments from first to last node
            if weighting:
                # Use the 'weight' for finding the shortest path
                path_dist = sum([G.es[e]['ori_length'] for e in path_e])  # Use 'ori_length' for distance
            else:
                path_dist = sum([G.es[e]['weight'] for e in path_e])  # Fallback to 'weight' if weighting is False
            
            if path_dist > 0:
                poi_dist[(path_n[0], path_n[-1])] = path_dist
            
    temp = sorted(poi_dist.items(), key = lambda x: x[1])
    # Back to ids
    output = []
    for p in temp:
        output.append([(G.vs[p[0][0]]["id"], G.vs[p[0][1]]["id"]), p[1]])
    
    if return_distances:
        return output
    else:
        return [o[0] for o in output]





# ANALYSIS

def rotate_grid(p, origin = (0, 0), degrees = 0):
        """Rotate a list of points around an origin (in 2D). 
        
        Parameters:
            p (tuple or list of tuples): (x,y) coordinates of points to rotate
            origin (tuple): (x,y) coordinates of rotation origin
            degrees (int or float): degree (clockwise)

        Returns:
            ndarray: the rotated points, as an ndarray of 1x2 ndarrays
        """
        # https://stackoverflow.com/questions/34372480/rotate-point-about-another-point-in-degrees-python
        angle = np.deg2rad(-degrees)
        R = np.array([[np.cos(angle), -np.sin(angle)],
                      [np.sin(angle),  np.cos(angle)]])
        o = np.atleast_2d(origin)
        p = np.atleast_2d(p)
        return np.squeeze((R @ (p.T-o.T) + o.T).T)


# Two functions from: https://github.com/gboeing/osmnx-examples/blob/v0.11/notebooks/17-street-network-orientations.ipynb
def reverse_bearing(x):
    return x + 180 if x < 180 else x - 180

def count_and_merge(n, bearings):
    # make twice as many bins as desired, then merge them in pairs
    # prevents bin-edge effects around common values like 0° and 90°
    n = n * 2
    bins = np.arange(n + 1) * 360 / n
    count, _ = np.histogram(bearings, bins=bins)
    
    # move the last bin to the front, so eg 0.01° and 359.99° will be binned together
    count = np.roll(count, 1)
    return count[::2] + count[1::2]


def calculate_directness(G, numnodepairs = 500):
    """Calculate directness on G over all connected node pairs in indices. This calculation method divides the total sum of euclidian distances by total sum of network distances.
    """
    
    indices = random.sample(list(G.vs), min(numnodepairs, len(G.vs)))

    poi_edges = []
    total_distance_direct = 0
    for c, v in enumerate(indices):
        poi_edges.append(G.get_shortest_paths(v, indices[c:], weights = "weight", output = "epath"))
        temp = G.get_shortest_paths(v, indices[c:], weights = "weight", output = "vpath")
        try:
            total_distance_direct += sum(dist_vector([(G.vs[t[0]]["y"], G.vs[t[0]]["x"]) for t in temp], [(G.vs[t[-1]]["y"], G.vs[t[-1]]["x"]) for t in temp])) # must be in format lat,lon = y, x
        except: # Rarely, routing does not work. Unclear why.
            pass
    total_distance_network = 0
    for paths_e in poi_edges:
        for path_e in paths_e:
            # Sum up distances of path segments from first to last node
            total_distance_network += sum([G.es[e]['weight'] for e in path_e])
    
    return total_distance_direct / total_distance_network

def calculate_directness_linkwise(G, numnodepairs = 500):
    """Calculate directness on G over all connected node pairs in indices. This is maybe the common calculation method: It takes the average of linkwise euclidian distances divided by network distances.

        If G has multiple components, node pairs in different components are discarded.
    """

    indices = random.sample(list(G.vs), min(numnodepairs, len(G.vs)))

    directness_links = np.zeros(int((len(indices)*(len(indices)-1))/2))
    ind = 0
    for c, v in enumerate(indices):
        poi_edges = G.get_shortest_paths(v, indices[c:], weights = "weight", output = "epath")
        for c_delta, path_e in enumerate(poi_edges[1:]): # Discard first empty list because it is the node to itself
            if path_e: # if path is non-empty, meaning the node pair is in the same component
                distance_network = sum([G.es[e]['weight'] for e in path_e]) # sum over all edges of path
                distance_direct = dist(v, indices[c+c_delta+1]) # dist first to last node, must be in format lat,lon = y, x

                directness_links[ind] = distance_direct / distance_network
                ind += 1
    directness_links = directness_links[:ind] # discard disconnected node pairs

    return np.mean(directness_links)


def listmean(lst): 
    try: return sum(lst) / len(lst)
    except: return 0

def calculate_coverage_edges(G, buffer_m = 500, return_cov = False, G_prev = ig.Graph(), cov_prev = Polygon()):
    """Calculates the area and shape covered by the graph's edges.
    If G_prev and cov_prev are given, only the difference between G and G_prev are calculated, then added to cov_prev.
    """

    G_added = copy.deepcopy(G)
    delete_overlaps(G_added, G_prev)

    # https://gis.stackexchange.com/questions/121256/creating-a-circle-with-radius-in-metres
    loncenter = listmean([v["x"] for v in G.vs])
    latcenter = listmean([v["y"] for v in G.vs])
    local_azimuthal_projection = "+proj=aeqd +R=6371000 +units=m +lat_0={} +lon_0={}".format(latcenter, loncenter)
    # Use transformer: https://gis.stackexchange.com/questions/127427/transforming-shapely-polygon-and-multipolygon-objects
    wgs84_to_aeqd = pyproj.Transformer.from_proj(
        pyproj.Proj("+proj=longlat +datum=WGS84 +no_defs"),
        pyproj.Proj(local_azimuthal_projection))
    aeqd_to_wgs84 = pyproj.Transformer.from_proj(
        pyproj.Proj(local_azimuthal_projection),
        pyproj.Proj("+proj=longlat +datum=WGS84 +no_defs"))
    edgetuples = [((e.source_vertex["x"], e.source_vertex["y"]), (e.target_vertex["x"], e.target_vertex["y"])) for e in G_added.es]
    # Shapely buffer seems slow for complex objects: https://stackoverflow.com/questions/57753813/speed-up-shapely-buffer
    # Therefore we buffer piecewise.
    cov_added = Polygon()
    for c, t in enumerate(edgetuples):
        # if cov.geom_type == 'MultiPolygon' and c % 1000 == 0: print(str(c)+"/"+str(len(edgetuples)), sum([len(pol.exterior.coords) for pol in cov]))
        # elif cov.geom_type == 'Polygon' and c % 1000 == 0: print(str(c)+"/"+str(len(edgetuples)), len(pol.exterior.coords))
        buf = ops.transform(aeqd_to_wgs84.transform, ops.transform(wgs84_to_aeqd.transform, LineString(t)).buffer(buffer_m))
        cov_added = ops.unary_union([cov_added, Polygon(buf)])

    # Merge with cov_prev
    if not cov_added.is_empty: # We need this check because apparently an empty Polygon adds an area.
        cov = ops.unary_union([cov_added, cov_prev])
    else:
        cov = cov_prev

    cov_transformed = ops.transform(wgs84_to_aeqd.transform, cov)
    covered_area = cov_transformed.area / 1000000 # turn from m2 to km2

    if return_cov:
        return (covered_area, cov)
    else:
        return covered_area


def calculate_poiscovered(G, cov, nnids):
    """Calculates how many nodes, given by nnids, are covered by the shapely (multi)polygon cov
    """
    
    pois_indices = set()
    for poi in nnids:
        pois_indices.add(G.vs.find(id = poi).index)

    poiscovered = 0
    for poi in pois_indices:
        v = G.vs[poi]
        if Point(v["x"], v["y"]).within(cov):
            poiscovered += 1
    
    return poiscovered


def calculate_efficiency_global(G, numnodepairs = 500, normalized = True):
    """Calculates global network efficiency.
    If there are more than numnodepairs nodes, measure over pairings of a 
    random sample of numnodepairs nodes.
    """

    if G is None: return 0
    if G.vcount() > numnodepairs:
        nodeindices = random.sample(list(G.vs.indices), numnodepairs)
    else:
        nodeindices = list(G.vs.indices)
    d_ij = G.shortest_paths(source = nodeindices, target = nodeindices, weights = "weight")
    d_ij = [item for sublist in d_ij for item in sublist] # flatten

    ### Check if d_ij contains valid distances
    if not d_ij: return 0  # No distances available
    ###

    EG = sum([1/d for d in d_ij if d != 0])
    if not normalized: return EG
    pairs = list(itertools.permutations(nodeindices, 2))
    if len(pairs) < 1: return 0
    l_ij = dist_vector([(G.vs[p[0]]["y"], G.vs[p[0]]["x"]) for p in pairs],
                            [(G.vs[p[1]]["y"], G.vs[p[1]]["x"]) for p in pairs]) # must be in format lat,lon = y,x
    EG_id = sum([1/l for l in l_ij if l != 0])
    
    # re comment this block later
    #if (EG / EG_id) > 1: # This should not be allowed to happen!
    #    pp.pprint(d_ij)
    #    pp.pprint(l_ij)
    #    pp.pprint([e for e in G.es])
    #    print(pairs)
    #    print([(G.vs[p[0]]["y"], G.vs[p[0]]["x"]) for p in pairs],
    #                         [(G.vs[p[1]]["y"], G.vs[p[1]]["x"]) for p in pairs]) # must be in format lat,lon = y,x
    #    print(EG, EG_id)
    #   sys.exit()
    # assert EG / EG_id <= 1, "Normalized EG > 1. This should not be possible."




    return EG / EG_id


def calculate_efficiency_local(G, numnodepairs = 500, normalized = True):
    """Calculates local network efficiency.
    If there are more than numnodepairs nodes, measure over pairings of a 
    random sample of numnodepairs nodes.
    """

    if G is None: return 0
    if G.vcount() > numnodepairs:
        nodeindices = random.sample(list(G.vs.indices), numnodepairs)
    else:
        nodeindices = list(G.vs.indices)
    EGi = []
    vcounts = []
    ecounts = []
    for i in nodeindices:
        if len(G.neighbors(i)) > 1: # If we have a nontrivial neighborhood
            G_induced = G.induced_subgraph(G.neighbors(i))
            EGi.append(calculate_efficiency_global(G_induced, numnodepairs, normalized))
    return listmean(EGi)

def calculate_metrics(
    G, GT_abstract, G_big, nnids, calcmetrics={"length": 0, "length_lcc": 0, "coverage": 0, "directness": 0,
                                               "directness_lcc": 0, "poi_coverage": 0, "components": 0,
                                               "overlap_biketrack": 0, "overlap_bikeable": 0, "efficiency_global": 0,
                                               "efficiency_local": 0, "directness_lcc_linkwise": 0,
                                               "directness_all_linkwise": 0, "overlap_neighbourhood": 0},
    buffer_walk=500, numnodepairs=500, verbose=False, return_cov=True, G_prev=ig.Graph(),
    cov_prev=Polygon(), ignore_GT_abstract=False, Gexisting={}, Gneighbourhoods=None
):
    """Calculates all metrics (using the keys from calcmetrics)."""

    output = {key: 0 for key in calcmetrics}
    cov = Polygon()

    # Check that the graph has links (sometimes we have an isolated node)
    if G.ecount() > 0 and GT_abstract.ecount() > 0:
        # Get LCC
        cl = G.clusters()
        LCC = cl.giant()

        # EFFICIENCY
        if not ignore_GT_abstract:
            if verbose and ("efficiency_global" in calcmetrics or "efficiency_local" in calcmetrics): print("Calculating efficiency...")
            if "efficiency_global" in calcmetrics:
                output["efficiency_global"] = calculate_efficiency_global(GT_abstract, numnodepairs)
            if "efficiency_local" in calcmetrics:
                output["efficiency_local"] = calculate_efficiency_local(GT_abstract, numnodepairs) 
        
        # EFFICIENCY ROUTED
        if verbose and ("efficiency_global_routed" in calcmetrics or "efficiency_local_routed" in calcmetrics): print("Calculating efficiency (routed)...")
        if "efficiency_global_routed" in calcmetrics:
            try:
                output["efficiency_global_routed"] = calculate_efficiency_global(simplify_ig(G), numnodepairs)
            except:
                print("Problem with efficiency_global_routed.") 
        if "efficiency_local_routed" in calcmetrics:
            try:
                output["efficiency_local_routed"] = calculate_efficiency_local(simplify_ig(G), numnodepairs)
            except:
                print("Problem with efficiency_local_routed.")

        # LENGTH
        if verbose and ("length" in calcmetrics or "length_lcc" in calcmetrics): print("Calculating length...")
        if "length" in calcmetrics:
            output["length"] = sum([e['weight'] for e in G.es])
        if "length_lcc" in calcmetrics:
            if len(cl) > 1:
                output["length_lcc"] = sum([e['weight'] for e in LCC.es])
            else:
                output["length_lcc"] = output["length"]
        
        # COVERAGE
        if "coverage" in calcmetrics:
            if verbose: print("Calculating coverage...")
            covered_area, cov = calculate_coverage_edges(G, buffer_walk, return_cov, G_prev, cov_prev)
            output["coverage"] = covered_area

            # OVERLAP WITH EXISTING NETS
            if Gexisting:
                if "overlap_biketrack" in calcmetrics:
                    try:
                        output["overlap_biketrack"] = edge_lengths(intersect_igraphs(Gexisting["biketrack"], G))
                    except:  # If there is not bike infrastructure, set to zero
                        output["overlap_biketrack"] = 0
                if "overlap_bikeable" in calcmetrics:
                    try:
                        output["overlap_bikeable"] = edge_lengths(intersect_igraphs(Gexisting["bikeable"], G))
                    except:  # If there is not bikeable infrastructure, set to zero
                        output["overlap_bikeable"] = 0

        # OVERLAP WITH NEIGHBOURHOOD NETWORK
        if Gneighbourhoods and "overlap_neighbourhood" in calcmetrics:
            if verbose: print("Calculating overlap_neighbourhood...")
            try:
                output["overlap_neighbourhood"] = edge_lengths(intersect_igraphs(Gneighbourhoods, G))
            except:  # If there are issues with intersecting graphs, set to zero
                output["overlap_neighbourhood"] = 0

        # POI COVERAGE
        if "poi_coverage" in calcmetrics:
            if verbose: print("Calculating POI coverage...")
            output["poi_coverage"] = calculate_poiscovered(G_big, cov, nnids)

        # COMPONENTS
        if "components" in calcmetrics:
            if verbose: print("Calculating components...")
            output["components"] = len(list(G.components()))
        
        # DIRECTNESS
        if verbose and ("directness" in calcmetrics or "directness_lcc" in calcmetrics): print("Calculating directness...")
        if "directness" in calcmetrics:
            output["directness"] = calculate_directness(G, numnodepairs)
        if "directness_lcc" in calcmetrics:
            if len(cl) > 1:
                output["directness_lcc"] = calculate_directness(LCC, numnodepairs)
            else:
                output["directness_lcc"] = output["directness"]

        # DIRECTNESS LINKWISE
        if verbose and ("directness_lcc_linkwise" in calcmetrics): print("Calculating directness linkwise...")
        if "directness_lcc_linkwise" in calcmetrics:
            if len(cl) > 1:
                output["directness_lcc_linkwise"] = calculate_directness_linkwise(LCC, numnodepairs)
            else:
                output["directness_lcc_linkwise"] = calculate_directness_linkwise(G, numnodepairs)
        if verbose and ("directness_all_linkwise" in calcmetrics): print("Calculating directness linkwise (all components)...")
        if "directness_all_linkwise" in calcmetrics:
            if "directness_lcc_linkwise" in calcmetrics and len(cl) <= 1:
                output["directness_all_linkwise"] = output["directness_lcc_linkwise"]
            else:  # we have >1 components
                output["directness_all_linkwise"] = calculate_directness_linkwise(G, numnodepairs)

    if return_cov: 
        return output, cov
    else:
        return output



def overlap_linepoly(l, p):
    """Calculates the length of shapely LineString l falling inside the shapely Polygon p
    """
    return p.intersection(l).length if l.length else 0


def edge_lengths(G):
    """Returns the total length of edges in an igraph graph.
    """
    return sum([e['weight'] for e in G.es])


def intersect_igraphs(G1, G2):
    """Generates the graph intersection of igraph graphs G1 and G2, copying also link and node attributes.
    """
    # Ginter = G1.__and__(G2) # This does not work with attributes.
    if G1.ecount() > G2.ecount(): # Iterate through edges of the smaller graph
        G1, G2 = G2, G1
    inter_nodes = set()
    inter_edges = []
    inter_edge_attributes = {}
    inter_node_attributes = {}
    edge_attribute_name_list = G2.edge_attributes()
    node_attribute_name_list = G2.vertex_attributes()
    for edge_attribute_name in edge_attribute_name_list:
        inter_edge_attributes[edge_attribute_name] = []
    for node_attribute_name in node_attribute_name_list:
        inter_node_attributes[node_attribute_name] = []
    for e in list(G1.es):
        n1_id = e.source_vertex["id"]
        n2_id = e.target_vertex["id"]
        try:
            n1_index = G2.vs.find(id = n1_id).index
            n2_index = G2.vs.find(id = n2_id).index
        except ValueError:
            continue
        if G2.are_connected(n1_index, n2_index):
            inter_edges.append((n1_index, n2_index))
            inter_nodes.add(n1_index)
            inter_nodes.add(n2_index)
            edge_attributes = e.attributes()
            for edge_attribute_name in edge_attribute_name_list:
                inter_edge_attributes[edge_attribute_name].append(edge_attributes[edge_attribute_name])

    # map nodeids to first len(inter_nodes) integers
    idmap = {n_index:i for n_index,i in zip(inter_nodes, range(len(inter_nodes)))}

    G_inter = ig.Graph()
    G_inter.add_vertices(len(inter_nodes))
    G_inter.add_edges([(idmap[e[0]], idmap[e[1]]) for e in inter_edges])
    for edge_attribute_name in edge_attribute_name_list:
        G_inter.es[edge_attribute_name] = inter_edge_attributes[edge_attribute_name]

    for n_index in idmap.keys():
        v = G2.vs[n_index]
        node_attributes = v.attributes()
        for node_attribute_name in node_attribute_name_list:
            inter_node_attributes[node_attribute_name].append(node_attributes[node_attribute_name])
    for node_attribute_name in node_attribute_name_list:
        G_inter.vs[node_attribute_name] = inter_node_attributes[node_attribute_name]

    return G_inter


def calculate_metrics_additively(
    Gs, GT_abstracts, prune_quantiles, G_big, nnids, buffer_walk=500, numnodepairs=500, verbose=False, 
    return_cov=True, Gexisting={}, Gneighbourhoods=None,
    output={
        "length": [], "length_lcc": [], "coverage": [], "directness": [], "directness_lcc": [],
        "poi_coverage": [], "components": [], "overlap_biketrack": [], "overlap_bikeable": [],
        "efficiency_global": [], "efficiency_local": [], "efficiency_global_routed": [], 
        "efficiency_local_routed": [], "directness_lcc_linkwise": [], "directness_all_linkwise": [],
        "overlap_neighbourhood": []  # Add the new metric here
    }
):
    """Calculates all metrics, additively. 
    Coverage differences are calculated in every step instead of the whole coverage.
    """

    # BICYCLE NETWORKS
    covs = {}  # Covers using buffer_walk
    cov_prev = Polygon()
    GT_prev = ig.Graph()

    for GT, GT_abstract, prune_quantile in zip(Gs, GT_abstracts, tqdm(prune_quantiles, desc="Bicycle networks", leave=False)):
        if verbose: print("Calculating bike network metrics for quantile " + str(prune_quantile))
        metrics, cov = calculate_metrics(
            GT, GT_abstract, G_big, nnids, output, buffer_walk, numnodepairs, verbose, 
            return_cov, GT_prev, cov_prev, False, Gexisting, Gneighbourhoods
        )

        for key in output.keys():
            output[key].append(metrics[key])
        covs[prune_quantile] = cov
        cov_prev = copy.deepcopy(cov)
        GT_prev = copy.deepcopy(GT)

    return output, covs


def generate_video(placeid, imgname, vformat = "webm", duplicatelastframe = 5, verbose = True):
    """Generate a video from a set of images using OpenCV
    """
    # Code adapted from: https://stackoverflow.com/questions/44947505/how-to-make-a-movie-out-of-images-in-python#44948030
    
    images = [img for img in os.listdir(PATH["plots_networks"] + placeid + "/") if img.startswith(placeid + imgname)]
    images.sort()
    frame = cv2.imread(os.path.join(PATH["plots_networks"] + placeid + "/", images[0]))
    height, width, layers = frame.shape

    if vformat == "webm":
        # https://stackoverflow.com/questions/49530857/python-opencv-video-format-play-in-browser
        fourcc = cv2.VideoWriter_fourcc(*'vp80')
        video = cv2.VideoWriter(PATH["videos"] + placeid + "/" + placeid + imgname + '.webm', fourcc, 10, (width, height))
    elif vformat == "mp4":
        # https://www.pyimagesearch.com/2016/02/22/writing-to-video-with-opencv/#comment-390650
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(PATH["videos"] + placeid + "/" + placeid + imgname + '.mp4', fourcc, 10, (width, height))

    for image in images:
        video.write(cv2.imread(os.path.join(PATH["plots_networks"] + placeid + "/", image)))
    # Add the last frame duplicatelastframe more times:
    for i in range(0, duplicatelastframe):
        video.write(cv2.imread(os.path.join(PATH["plots_networks"] + placeid + "/", images[-1])))

    cv2.destroyAllWindows()
    video.release()
    if verbose:
        print("Video " + placeid + imgname + '.' + vformat + ' generated from ' + str(len(images)) + " frames.")



def write_result(res, mode, placeid, poi_source, prune_measure, suffix, dictnested={}, weighting=None):
    """Write results (pickle or dict to csv)
    """
    if mode == "pickle":
        openmode = "wb"
    else:
        openmode = "w"

    # Modify filename based on weighting flag
    weighting_str = "_weighted" if weighting else ""
    
    # Construct the filename based on whether prune_measure is provided or not
    if poi_source:
        if prune_measure:
            filename = placeid + '_poi_' + poi_source + "_" + prune_measure + weighting_str + suffix
        else:
            filename = placeid + '_poi_' + poi_source + weighting_str + suffix
    else:
        if prune_measure:
            filename = placeid + "_" + prune_measure + weighting_str + suffix
        else:
            filename = placeid + weighting_str + suffix

    with open(PATH["results"] + placeid + "/" + filename, openmode) as f:
        if mode == "pickle":
            pickle.dump(res, f)
        elif mode == "dict":
            w = csv.writer(f)
            w.writerow(res.keys())
            try:  # dict with list values
                w.writerows(zip(*res.values()))
            except:  # dict with single values
                w.writerow(res.values())
        elif mode == "dictnested":
            fields = ['network'] + list(dictnested.keys())
            w = csv.DictWriter(f, fields)
            w.writeheader()
            for key, val in sorted(res.items()):
                row = {'network': key}
                row.update(val)
                w.writerow(row)

                

def write_result_covers(res, mode, placeid, suffix, dictnested={}, weighting=None):
    # makes results format place_existing_covers_weighted.csv etc. 
    """Write results (pickle or dict to csv), with _weighted before the file extension if needed
    """
    if mode == "pickle":
        openmode = "wb"
        file_extension = ".pickle"
    else:
        openmode = "w"
        file_extension = ".csv"

    # Modify filename to append '_weighted' before the file extension if weighting is True
    if weighting:
        suffix = suffix.replace(file_extension, "") + "_weighted" + file_extension
    else:
        suffix += file_extension

    # Construct the filename
    filename = placeid + "_" + suffix

    # Write the file
    with open(PATH["results"] + placeid + "/" + filename, openmode) as f:
        if mode == "pickle":
            pickle.dump(res, f)
        elif mode == "dict":
            w = csv.writer(f)
            w.writerow(res.keys())
            try:  # dict with list values
                w.writerows(zip(*res.values()))
            except:  # dict with single values
                w.writerow(res.values())
        elif mode == "dictnested":
            # Writing nested dictionary to CSV
            fields = ['network'] + list(dictnested.keys())
            w = csv.DictWriter(f, fields)
            w.writeheader()
            for key, val in sorted(res.items()):
                row = {'network': key}
                row.update(val)
                w.writerow(row)




def gdf_to_geojson(gdf, properties):
    """Turn a gdf file into a GeoJSON.
    The gdf must consist only of geometries of type Point.
    Adapted from: https://geoffboeing.com/2015/10/exporting-python-data-geojson/
    """
    geojson = {'type':'FeatureCollection', 'features':[]}
    for _, row in gdf.iterrows():
        feature = {'type':'Feature',
                   'properties':{},
                   'geometry':{'type':'Point',
                               'coordinates':[]}}
        feature['geometry']['coordinates'] = [row.geometry.x, row.geometry.y]
        for prop in properties:
            feature['properties'][prop] = row[prop]
        geojson['features'].append(feature)
    return geojson



def ig_to_shapely(G):
    """Turn an igraph graph G to a shapely LineString
    """
    edgetuples = [((e.source_vertex["x"], e.source_vertex["y"]), (e.target_vertex["x"], e.target_vertex["y"])) for e in G.es]
    G_shapely = LineString()
    for t in edgetuples:
        G_shapely = ops.unary_union([G_shapely, LineString(t)])
    return G_shapely


# Neighbourhoods

def load_neighbourhoods(path):
    """
    Load all neighbourhoods geopackages with 'scored_neighbourhoods_' in the filename. 

    Parameters:
        path (str): The base path where the GeoPackage files are located.
    Returns:
        dict: A dictionary with cleaned filenames as keys and GeoDataFrames as values.
    """
    # Construct the path to the GeoPackage directory
    gpkg_dir = os.path.join(path)
    geopackages = {}
    # Define the prefix to remove
    prefix = "scored_neighbourhoods_"

    # Check if the directory exists
    if os.path.exists(gpkg_dir):
        # Iterate over all files in the directory
        for filename in os.listdir(gpkg_dir):
            if filename.endswith('.gpkg') and "scored_neighbourhoods_" in filename:  # Check for GeoPackage files with the desired prefix
                # Construct the full path to the GeoPackage file
                gpkg_path = os.path.join(gpkg_dir, filename)
                try:
                    # Load the GeoPackage into a GeoDataFrame
                    gdf = gpd.read_file(gpkg_path)
                    
                    # Remove the .gpkg extension from the filename
                    city_name = os.path.splitext(filename)[0]
                    
                    # Remove the "scored_neighbourhoods_" prefix if it exists
                    if city_name.startswith(prefix):
                        city_name = city_name[len(prefix):]
                    
                    # Add the cleaned filename (city_name) and GeoDataFrame to the dictionary
                    geopackages[city_name] = gdf
                except Exception as e:
                    print(f"Error loading GeoPackage {filename}: {e}")
    else:
        print(f"Directory does not exist: {gpkg_dir}")

    print(f"{len(geopackages)} Cities loaded")
    
    return geopackages

print("Loaded functions.\n")



def nearest_edge_between_polygons(G, poly1, poly2):
    """Find the shortest path between the edges of two polygons based on routing distance."""
    min_dist = float('inf')
    best_pair = None

    # Get edges of both polygons as lists of coordinate pairs
    poly1_edges = list(zip(poly1.exterior.coords[:-1], poly1.exterior.coords[1:]))
    poly2_edges = list(zip(poly2.exterior.coords[:-1], poly2.exterior.coords[1:]))

    # Iterate over all edges of both polygons
    for edge1 in poly1_edges:
        for edge2 in poly2_edges:
            # Use existing graph's shortest path function between edge points
            sp = G.get_shortest_paths(edge1[0], edge2[0], weights='weight', output='vpath')
            dist = sum([G.es[e]["weight"] for e in sp[0]]) # Add the weights of the shortest path

            if dist < min_dist:
                min_dist = dist
                best_pair = (edge1[0], edge2[0])

    return best_pair, min_dist





def greedy_triangulation_polygon_routing(G, pois, weighting=None, prune_quantiles = [1], prune_measure = "betweenness"):
    """Greedy Triangulation (GT) of a graph G's node subset pois,
    then routing to connect the GT (up to a quantile of betweenness
    betweenness_quantile).
    G is an ipgraph graph, pois is a list of node ids.
    
    The GT connects pairs of nodes in ascending order of their distance provided
    that no edge crossing is introduced. It leads to a maximal connected planar
    graph, while minimizing the total length of edges considered. 
    See: cardillo2006spp
    
    Distance here is routing distance, while edge crossing is checked on an abstract 
    level.
    """
    
    if len(pois) < 2: return ([], []) # We can't do anything with less than 2 POIs

    # GT_abstract is the GT with same nodes but euclidian links to keep track of edge crossings
    pois_indices = set()
    for poi in pois:
        pois_indices.add(G.vs.find(id = poi).index)
    G_temp = copy.deepcopy(G)
    for e in G_temp.es: # delete all edges
        G_temp.es.delete(e)
        
    poipairs = poipairs_by_distance(G, pois, weighting, True)
    if len(poipairs) == 0: return ([], [])

    if prune_measure == "random":
        # run the whole GT first
        GT = copy.deepcopy(G_temp.subgraph(pois_indices))
        for poipair, poipair_distance in poipairs:
            poipair_ind = (GT.vs.find(id = poipair[0]).index, GT.vs.find(id = poipair[1]).index)
            if not new_edge_intersects(GT, (GT.vs[poipair_ind[0]]["x"], GT.vs[poipair_ind[0]]["y"], GT.vs[poipair_ind[1]]["x"], GT.vs[poipair_ind[1]]["y"])):
                GT.add_edge(poipair_ind[0], poipair_ind[1], weight = poipair_distance)
        # create a random order for the edges
        random.seed(0) # const seed for reproducibility
        edgeorder = random.sample(range(GT.ecount()), k = GT.ecount())
    else: 
        edgeorder = False
    
    GT_abstracts = []
    GTs = []
    for prune_quantile in tqdm(prune_quantiles, desc = "Greedy triangulation", leave = False):
        GT_abstract = copy.deepcopy(G_temp.subgraph(pois_indices))
        GT_abstract = greedy_triangulation(GT_abstract, poipairs, prune_quantile, prune_measure, edgeorder)
        GT_abstracts.append(GT_abstract)
        
        # Get node pairs we need to route, sorted by distance
        routenodepairs = {}
        for e in GT_abstract.es:
            routenodepairs[(e.source_vertex["id"], e.target_vertex["id"])] = e["weight"]
        routenodepairs = sorted(routenodepairs.items(), key = lambda x: x[1])

        # Do the routing
        GT_indices = set()
        for poipair, poipair_distance in routenodepairs:
            poipair_ind = (G.vs.find(id = poipair[0]).index, G.vs.find(id = poipair[1]).index)
            # debug
            #print(f"Edge weights before routing: {G.es['weight'][:10]}")  # Prints first 10 weights
            #print(f"Routing between: {poipair[0]} and {poipair[1]} with distance: {poipair_distance}")
            sp = set(G.get_shortest_paths(poipair_ind[0], poipair_ind[1], weights = "weight", output = "vpath")[0])
            #print(f"Shortest path between {poipair[0]} and {poipair[1]}: {sp}")

            GT_indices = GT_indices.union(sp)

        GT = G.induced_subgraph(GT_indices)
        GTs.append(GT)
    
    return (GTs, GT_abstracts)
    

def get_neighbourhood_centroids(gdf):
    """
    Find the centroid of each neighbourhood

    Parameters:
        gdf (GeoDataFrame): A GeoDataFrame containing the city's polygons (neighbourhoods).

    Returns:
        GeoDataFrame: A GeoDataFrame containing the centroids moved to the nearest edge.
    """
    centroids = gdf.geometry.centroid  # Calculate centroids for each polygon
    centroids_gdf = gpd.GeoDataFrame({'neighbourhood_id': gdf['neighbourhood_id'], 'geometry': centroids}, crs=gdf.crs) 
    
    return centroids_gdf 

def prepare_neighbourhoods(cities):
    """
    Convert columns from strings to numbers. Quirk of exporting geopackages with numbers...

    Parameters:
        cities (dict): A dictionary with filenames as keys and GeoDataFrames as values.
    """
    for city_name, gdf in cities.items():
        for column in gdf.columns:
            if column != 'geometry':
                try:
                    gdf[column] = pd.to_numeric(gdf[column], errors='coerce')
                except Exception as e:
                    print(f"Error converting column '{column}' in '{city_name}': {e}")

    return cities

    
def get_neighbourhood_streets(gdf, debug=False):
    """"
    Get all the streets within each neighbourhood.

    Parameters:
        gdf (GeoDataFrame): A GeoDataFrame containing neighbourhoods.
    Returns:            
        gdf of nodes and edges within neighbourhoods
    """ 
    # Add a unique ID column to the GeoDataFrame
    print(f"GeoDataFrame shape before adding ID: {gdf.shape}")

    gdf['ID'] = range(1, len(gdf) + 1)  # Adding ID column starting from 1

    # create bounding box slightly larger than neighbourhoods
    gdf_mercator = gdf.to_crs(epsg=3857)
    gdf_mercator = gdf_mercator.buffer(1000)
    gdf_buffered = gpd.GeoDataFrame(geometry=gdf_mercator, crs="EPSG:3857").to_crs(epsg=4326)
    minx, miny, maxx, maxy = gdf_buffered.total_bounds
    
    # get driving network (we're only interested in streets cars could be on)
    network = ox.graph_from_bbox(maxy, miny, maxx, minx, network_type='drive')
    nodes, edges = ox.graph_to_gdfs(network)
    edges = gpd.sjoin(edges, gdf[['ID', 'overall_score', 'geometry']], how="left", op='intersects')

    if debug == True:
        unique_ids = edges['ID'].dropna().unique()
        np.random.seed(42) 
        random_colors = {ID: mcolors.to_hex(np.random.rand(3)) for ID in unique_ids}
        edges['color'] = edges['ID'].map(random_colors)
        edges['color'] = edges['color'].fillna('#808080')  # Gray for NaN values
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        edges.plot(ax=ax, color=edges['color'], legend=False) 
        ax.set_title('Edges colored randomly by Neighbourhood ID')
        plt.show()

    return nodes, edges


def get_neighbourhood_street_graph(gdf, debug=False):
    """"
    Get all the streets within each neighbourhood.

    Parameters:
        gdf (GeoDataFrame): A GeoDataFrame containing neighbourhoods.
    Returns:            
        gdf of nodes and edges within neighbourhoods
    """ 
    # Add a unique ID column to the GeoDataFrame
    print(f"GeoDataFrame shape before adding ID: {gdf.shape}")

    gdf['ID'] = range(1, len(gdf) + 1)  # Adding ID column starting from 1

    # create bounding box slightly larger than neighbourhoods
    gdf_mercator = gdf.to_crs(epsg=3857)
    gdf_mercator = gdf_mercator.buffer(1000)
    gdf_buffered = gpd.GeoDataFrame(geometry=gdf_mercator, crs="EPSG:3857").to_crs(epsg=4326)
    minx, miny, maxx, maxy = gdf_buffered.total_bounds
    
    # get driving network (we're only interested in streets cars could be on)
    network = ox.graph_from_bbox(maxy, miny, maxx, minx, network_type='drive')
    nodes, edges = ox.graph_to_gdfs(network)
    edges = gpd.sjoin(edges, gdf[['ID', 'overall_score', 'geometry']], how="left", op='intersects')

    if debug == True:
        unique_ids = edges['ID'].dropna().unique()
        np.random.seed(42) 
        random_colors = {ID: mcolors.to_hex(np.random.rand(3)) for ID in unique_ids}
        edges['color'] = edges['ID'].map(random_colors)
        edges['color'] = edges['color'].fillna('#808080')  # Gray for NaN values
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        edges.plot(ax=ax, color=edges['color'], legend=False) 
        ax.set_title('Edges colored randomly by Neighbourhood ID')
        plt.show()


    edges = edges.dropna(subset=['ID'])
    G = ox.graph_from_gdfs(nodes, edges)
    
    return nodes, edges, G

def get_neighbourhood_streets_split(gdf, debug):
    """"
    Get all the streets within each neighbourhood.

    Parameters:
        gdf (GeoDataFrame): A GeoDataFrame containing neighbourhoods.
    Returns:            
        gdf of nodes and edges within neighbourhoods
    """ 
    # add ID for export
    gdf['ID'] = range(1, len(gdf) + 1)  # Adding ID column starting from 1

    # create bounding box slightly larger than neighbourhoods
    gdf_mercator = gdf.to_crs(epsg=3857)
    gdf_mercator = gdf_mercator.buffer(1000)
    gdf_buffered = gpd.GeoDataFrame(geometry=gdf_mercator, crs="EPSG:3857").to_crs(epsg=4326)
    minx, miny, maxx, maxy = gdf_buffered.total_bounds
    
    # get street network (we want to consider all exit/entry points)
    network = ox.graph_from_bbox(maxy, miny, maxx, minx, network_type='all')
    nodes, edges = ox.graph_to_gdfs(network)
    def get_boundary_graph(network):
        """
        Create a graph from bounding roads.

        Args:
            network (networkx.Graph): The original graph.

        Returns:
            networkx.Graph: The boundary graph.
        """
        boundary_g = network.copy()
        # Define the conditions for keeping edges
        conditions = [
        (
            data.get('highway') in ['trunk', 'trunk_link', 'motorway', 'motorway_link', 'primary', 'primary_link',
                                    'secondary', 'secondary_link', 'tertiary', 'tertiary_link'] 
        ) or (
            data.get('maxspeed') in ['60 mph', '70 mph', '40 mph', 
                                    ('30 mph', '60 mph'), ('30 mph', '50 mph'), 
                                    ('70 mph', '50 mph'), ('40 mph', '60 mph'), 
                                    ('70 mph', '60 mph'), ('60 mph', '40 mph'),
                                    ('50 mph', '40 mph'), ('30 mph', '40 mph'),
                                    ('20 mph', '60 mph'), ('70 mph', '40 mph'), 
                                    ('30 mph', '70 mph')]
            ) 
            for u, v, k, data in boundary_g.edges(keys=True, data=True)
        ]
        # Keep only the edges that satisfy the conditions
        edges_to_remove = [
            (u, v, k) for (u, v, k), condition in zip(boundary_g.edges(keys=True), conditions) if not condition
        ]
        boundary_g.remove_edges_from(edges_to_remove)
        # Clean nodes by removing isolated nodes from the graph
        isolated_nodes = list(nx.isolates(boundary_g))
        boundary_g.remove_nodes_from(isolated_nodes)
        return boundary_g
    boundary_g = get_boundary_graph(network)
    filtered_g = network.copy()
    filtered_g.remove_edges_from(boundary_g.edges())
    filtered_g.remove_nodes_from(boundary_g.nodes())
    # Clip the graph to the boundary (but make the boundary slightly larger)
    filtered_g_edges = ox.graph_to_gdfs(filtered_g, nodes=False)
    filtered_g_nodes = ox.graph_to_gdfs(filtered_g, edges=False)
    filtered_g_edges = filtered_g_edges.clip(gdf)
    filtered_g_nodes = filtered_g_nodes.clip(gdf)

    # Add new nodes at the end of any edge which has been truncated
    # this is needed to ensure that the graph is correctly disconnected
    # at boundary roads
    def add_end_nodes(filtered_g_nodes, filtered_g_edges):
        # Create a GeoSeries of existing node geometries for spatial operations
        existing_node_geometries = gpd.GeoSeries(filtered_g_nodes.geometry.tolist())
        new_nodes = []
        new_edges = []
        # Iterate through each edge to check its endpoints
        for idx, edge in filtered_g_edges.iterrows():
            geometries = [edge.geometry] if isinstance(edge.geometry, LineString) else edge.geometry.geoms
            # Loop through each geometry in the edge
            for geom in geometries:
                u = geom.coords[0]  # Start point (first coordinate)
                v = geom.coords[-1]  # End point (last coordinate)
                # Check if the start point exists
                if not existing_node_geometries.contains(Point(u)).any():
                    # Create a new node at the start point
                    new_node = gpd.GeoDataFrame(geometry=[Point(u)], crs=filtered_g_nodes.crs)
                    new_node['id'] = f'new_{len(filtered_g_nodes) + len(new_nodes)}'  # Generate a unique id
                    new_node['x'] = u[0]
                    new_node['y'] = u[1]
                    new_nodes.append(new_node)
                # Check if the end point exists
                if not existing_node_geometries.contains(Point(v)).any():
                    # Create a new node at the end point
                    new_node = gpd.GeoDataFrame(geometry=[Point(v)], crs=filtered_g_nodes.crs)
                    new_node['id'] = f'new_{len(filtered_g_nodes) + len(new_nodes)}'  # Generate a unique id
                    new_node['x'] = v[0]
                    new_node['y'] = v[1]
                    new_nodes.append(new_node)
                # Add new edges to new_edges list if endpoints are new nodes
                new_edges.append((u, v, geom))  # Keep the geometry of the edge
        # Combine new nodes into a GeoDataFrame
        if new_nodes:
            new_nodes_gdf = pd.concat(new_nodes, ignore_index=True)
            filtered_g_nodes = gpd.GeoDataFrame(pd.concat([filtered_g_nodes, new_nodes_gdf], ignore_index=True))
        return filtered_g_nodes, filtered_g_edges
    filtered_g_nodes, filtered_g_edges = add_end_nodes(filtered_g_nodes, filtered_g_edges)
    # Rebuild graph with new end nodes
    filtered_g.clear()
    filtered_g = nx.MultiDiGraph()

    # add nodes and edges back in
    unique_nodes = set()
    for _, row in filtered_g_edges.iterrows():
        if row.geometry.type == 'LineString':
            coords = list(row.geometry.coords)
        elif row.geometry.type == 'MultiLineString':
            coords = [coord for line in row.geometry.geoms for coord in line.coords]
        unique_nodes.update(coords)
    # Add nodes with attributes
    for node in unique_nodes:
        if isinstance(node, tuple):
            x, y = node
            filtered_g.add_node(node, x=x, y=y, geometry=Point(x, y))
    # Add nodes from filtered_g_nodes
    for idx, row in filtered_g_nodes.iterrows():
        node_id = idx
        if node_id not in filtered_g.nodes:
            filtered_g.add_node(node_id, osmid=node_id, x=row.geometry.x, y=row.geometry.y, geometry=row.geometry)
    # Add edges
    for _, row in filtered_g_edges.iterrows():
        if row.geometry.type == 'LineString':
            coords = list(row.geometry.coords)
            for i in range(len(coords) - 1):
                filtered_g.add_edge(coords[i], coords[i + 1], geometry=row.geometry, osmid=row['osmid'])
        elif row.geometry.type == 'MultiLineString':
            for line in row.geometry.geoms:
                coords = list(line.coords)
                for i in range(len(coords) - 1):
                    filtered_g.add_edge(coords[i], coords[i + 1], geometry=line, osmid=row['osmid'])
    # Assign osmids to nodes with coordinate IDs
    # this ensure omsnx compatibility
    for node, data in filtered_g.nodes(data=True):
        if isinstance(node, tuple):
            # Find an edge that contains this node (dirty method of getting osmid)
            for u, v, key, edge_data in filtered_g.edges(keys=True, data=True):
                if node in [u, v]:
                    data['osmid'] = edge_data['osmid']
                    break
    filtered_g.graph['crs'] = 'EPSG:4326' # give the graph a crs
    neighbourhood_graphs = filtered_g
    nodes, edges = ox.graph_to_gdfs(filtered_g)
    # Set 'osmid' as the index, replacing the old index
    nodes = nodes.set_index('osmid', drop=True)

    edges = gpd.sjoin(edges, gdf[['ID', 'overall_score', 'geometry']], how="left", op='intersects')

    if debug == True:
        # plot out the network into its "neighbourhoods"
        network = filtered_g
        undirected_network = network.to_undirected()
        connected_components = list(nx.connected_components(undirected_network))
        colors = [f'#{random.randint(0, 0xFFFFFF):06x}' for _ in range(len(connected_components))]
        edge_color_map = {}
        for color, component in zip(colors, connected_components):
            component_edges = []
            for node in component:
                for neighbor in undirected_network.neighbors(node):
                    edge = (node, neighbor)
                    reverse_edge = (neighbor, node)
                    if edge in network.edges or reverse_edge in network.edges:
                        component_edges.append(edge)

            # Assign the same color to all edges in the component
            for edge in set(component_edges): 
                edge_color_map[edge] = color
        edge_colors = []
        for edge in network.edges:
            # Ensure we look for both directions in the edge color map
            edge_colors.append(edge_color_map.get(edge, edge_color_map.get((edge[1], edge[0]), 'black')))  # Default to black if not found

        # Draw the network without nodes, increase figsize for larger plot
        fig, ax = plt.subplots(figsize=(20, 15))  # Set the desired figure size
        ox.plot_graph(network, ax=ax, node_color='none', edge_color=edge_colors,
                    edge_linewidth=2, show=False)
        plt.show()

    return nodes, edges, neighbourhood_graphs




def get_exit_nodes(neighbourhoods, G_carall, neighbourhood_buffer_distance=10, street_buffer_distance=100):
    """
    Get nodes within a buffer of neighbourhood boundaries and street edges.

    Parameters:
    - neighbourhoods: dict, dictionary of neighbourhood GeoDataFrames
    - G_carall: OSMnx graph, the graph of the area
    - neighbourhood_buffer_distance: float, buffer distance in meters for neighbourhoods
    - street_buffer_distance: float, buffer distance in meters for streets

    Returns:
    - nodes_within_buffer: GeoDataFrame containing nodes within the specified buffer
    """
    
    # Load graph and set CRS if not present
    if 'crs' not in G_carall.graph:
        G_carall.graph['crs'] = 'epsg:4326'

    # Load neighbourhoods and convert graph to GeoDataFrames
    edges = ox.graph_to_gdfs(G_carall, nodes=False, edges=True)
    nodes = ox.graph_to_gdfs(G_carall, nodes=True, edges=False)

    # Add unique IDs to each polygon in neighbourhoods and buffer them
    boundary_buffers = {}
    for place_name, gdf in neighbourhoods.items():
        exploded_gdf = gdf.explode().reset_index(drop=True)
        exploded_gdf['neighbourhood_id'] = exploded_gdf.index  # Unique ID for each polygon
        buffer = exploded_gdf.boundary.to_crs(epsg=3857).buffer(neighbourhood_buffer_distance).to_crs(exploded_gdf.crs)  # Buffering
        boundary_buffers[place_name] = (buffer, exploded_gdf)

    # Combine all buffers into a single GeoDataFrame and set the geometry
    buffer_geometries = [boundary_buffers[place][0] for place in boundary_buffers]
    neighbourhood_geometries = [boundary_buffers[place][1]['neighbourhood_id'] for place in boundary_buffers]

    # Create a GeoDataFrame from the geometries
    boundary_buffers_gdf = gpd.GeoDataFrame(geometry=pd.concat(buffer_geometries, ignore_index=True))
    boundary_buffers_gdf['neighbourhood_id'] = pd.concat(neighbourhood_geometries, ignore_index=True)

    # Ensure CRS is set correctly
    nodes_within_buffer = gpd.sjoin(nodes, boundary_buffers_gdf, how='inner', op='intersects')

    street_buffers = {}
    for place_name, gdf in neighbourhoods.items():
        street_nodes, street_edges, neighbourhood_graph = get_neighbourhood_streets_split(gdf, debug=False)
        # Buffering edges with correct CRS
        street_buffer = street_edges.to_crs(epsg=3857).geometry.buffer(street_buffer_distance).to_crs(street_edges.crs)
        street_buffers[place_name] = gpd.GeoDataFrame(geometry=street_buffer, crs=street_edges.crs)

    streets_buffer_gdf = gpd.GeoDataFrame(
        pd.concat([gdf for gdf in street_buffers.values()]), 
        crs=next(iter(street_buffers.values())).crs
    )

    # Drop the 'index_right' column to avoid conflict
    if 'index_right' in nodes_within_buffer.columns:
        nodes_within_buffer = nodes_within_buffer.drop(columns=['index_right'])

    nodes_within_buffer = gpd.sjoin(nodes_within_buffer, streets_buffer_gdf, how='inner', op='intersects')
    # Clean up columns 
    if 'index_right0' in nodes_within_buffer.columns:
        nodes_within_buffer = nodes_within_buffer.drop(columns=['index_right0', 'index_right1', 'index_right2'], errors='ignore')

    return nodes_within_buffer


def greedy_triangulation_routing_GT_abstracts(G, pois, weighting=None, prune_quantiles=[1], prune_measure="betweenness"):
    """Generates Greedy Triangulation (GT_abstracts) of a graph G's node subset pois.
    This version focuses only on GT_abstracts without generating GTs.
    """

    if len(pois) < 2:
        return []  # We can't do anything with less than 2 POIs

    # Initialize the POI indices and an empty copy of G
    pois_indices = {G.vs.find(id=poi).index for poi in pois}
    G_temp = copy.deepcopy(G)
    for e in G_temp.es:
        G_temp.es.delete(e)  # Delete all edges in G_temp

    poipairs = poipairs_by_distance(G, pois, weighting, True)
    if not poipairs:
        return []

    # If prune_measure is "random", define edge order
    edgeorder = False
    if prune_measure == "random":
        GT = copy.deepcopy(G_temp.subgraph(pois_indices))
        for poipair, poipair_distance in poipairs:
            poipair_ind = (
                GT.vs.find(id=poipair[0]).index, 
                GT.vs.find(id=poipair[1]).index
            )
            if not new_edge_intersects(
                GT, (
                    GT.vs[poipair_ind[0]]["x"], 
                    GT.vs[poipair_ind[0]]["y"], 
                    GT.vs[poipair_ind[1]]["x"], 
                    GT.vs[poipair_ind[1]]["y"]
                )
            ):
                GT.add_edge(poipair_ind[0], poipair_ind[1], weight=poipair_distance)
        
        # Define a random edge order
        random.seed(0)  # Constant seed for reproducibility
        edgeorder = random.sample(range(GT.ecount()), k=GT.ecount())
    
    # Generate GT_abstracts for each prune_quantile
    GT_abstracts = []
    for prune_quantile in tqdm(prune_quantiles, desc="Greedy triangulation", leave=False):
        GT_abstract = copy.deepcopy(G_temp.subgraph(pois_indices))
        GT_abstract = greedy_triangulation(GT_abstract, poipairs, prune_quantile, prune_measure, edgeorder)
        GT_abstracts.append(GT_abstract)
    
    return GT_abstracts



def get_urban_areas(place):
    def set_location_boundary(place):
        """
        Sets up the location boundary by geocoding the given place and buffering it.

        Parameters:
        place (str): The name or address of the place to geocode.

        Returns:
        geopandas.GeoDataFrame: The buffered boundary of the location.
        """
        # Set location and get boundary
        boundary = ox.geocode_to_gdf(place)
        boundary = boundary.to_crs('3857') # we convert to EPSG 3857 to buffer in meters
        boundary_buffered = boundary.buffer(100) # Buffer boundary to prevent strange edge cases...

        return boundary_buffered, boundary

    ## get urban footprints from GUF

    def get_guf(place):
        """
        Retrieves a clipped GeoDataFrame of GUF urban areas within a specified place boundary.

        Parameters:
        - place (str): The name or address of the place to retrieve urban areas for.

        Returns:
        - gdf_clipped (GeoDataFrame): A GeoDataFrame containing the clipped urban areas within the specified place boundary.
        """

        # Step 1: Access the WMS Service
        wms_url = 'https://geoservice.dlr.de/eoc/land/wms?GUF04_DLR_v1_Mosaic'
        wms = WebMapService(wms_url, version='1.1.1')

        # Step 2: Identify the Layer with ID 102. This is the Global Urban Footprint layer GUF
        for layer_name, layer in wms.contents.items():
            if '102' in layer_name:
                print(f"Layer ID 102 found: {layer_name}")

        # Assuming 'GUF04_DLR_v1_Mosaic' is the layer with ID 102
        layer = 'GUF04_DLR_v1_Mosaic'  # Replace with the actual layer name if different

        # Step 3: Get the polygon boundary using osmnx

        boundary_gdf = ox.geocode_to_gdf(place)

        boundary = boundary_gdf.to_crs('EPSG:3857')
        # buffer boundary to ensure clips include riverlines which may act as borders between geographies
        boundary_buffered = boundary.buffer(100)
        boundary_buffered = boundary_buffered.to_crs('EPSG:4326')
        boundary_polygon = boundary_gdf.geometry[0]
        wms_boundary = boundary_buffered.geometry[0]

        # Convert the polygon to a bounding box
        minx, miny, maxx, maxy = wms_boundary.bounds

        # Step 4: Request the data from WMS using the bounding box
        width = 1024
        height = 1024
        response = wms.getmap(
            layers=[layer],
            srs='EPSG:4326',
            bbox=(minx, miny, maxx, maxy),
            size=(width, height),
            format='image/geotiff'
        )

        # Step 5: Load the Raster Data into Rasterio
        with MemoryFile(response.read()) as memfile:
            with memfile.open() as src:
                image = src.read(1)  # Read the first band
                transform = src.transform
                crs = src.crs

                # Clip the raster data to the polygon
                out_image, out_transform = rio_mask(src, [mapping(wms_boundary)], crop=True)  # Use renamed mask function
                out_meta = src.meta.copy()
                out_meta.update({"driver": "GTiff",
                                "height": out_image.shape[1],
                                "width": out_image.shape[2],
                                "transform": out_transform,
                                "crs": crs})

        # Step 6: Convert Raster to Vector
        mask_arr = (out_image[0] != 0).astype(np.uint8)  # Assuming non-zero values are urban areas

        shapes_gen = shapes(mask_arr, mask=mask_arr, transform=out_transform)

        polygons = []
        for geom, value in shapes_gen:
            polygons.append(shape(geom))

        # Create a GeoDataFrame from the polygons
        gdf = gpd.GeoDataFrame({'geometry': polygons}, crs=crs)

        # Step 7: Create Buffers Around Urban Areas
        buffer_distance = 100  # Buffer distance in meters (adjust as needed)
        gdf_buffered = gdf.copy()
        gdf_buffered['geometry'] = gdf['geometry'].buffer(buffer_distance)

        # Step 8: Clip the GeoDataFrame to the boundary of the place
        gdf_clipped = gpd.clip(gdf, boundary_gdf)

        return gdf_clipped

    ## get residential areas
    def get_residential_areas(polygon):
        polygon = polygon.to_crs('EPSG:4326')
        # Retrieve features from OpenStreetMap
        features = ox.features_from_polygon(polygon.iloc[0], tags={'landuse': 'residential'})
        
        # Convert features to a GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features)
        gdf = gdf.set_crs('EPSG:4326')
        
        return gdf



    ## join urban foot prints and residential areas
    # this is to create a single polygon of where neighbourhoods can be found within

    def join_geodataframes(gdf1, gdf2):
        # Ensure both GeoDataFrames have the exact same CRS
        target_crs = 'EPSG:4326'  # WGS 84
        gdf1 = gdf1.to_crs(target_crs)
        gdf2 = gdf2.to_crs(target_crs)
        
        # Concatenate GeoDataFrames
        joined_gdf = pd.concat([gdf1, gdf2], ignore_index=True)
        
        return gpd.GeoDataFrame(joined_gdf, crs=target_crs)





    ## create a small buffer to ensure all areas a captured correctly

    def buffer_geometries_in_meters(gdf, distance):
        # Define the World Mercator projected CRS
        projected_crs = 'EPSG:3857'  # World Mercator

        # Project to the new CRS
        gdf_projected = gdf.to_crs(projected_crs)
        
        # Buffer the geometries
        gdf_projected['geometry'] = gdf_projected['geometry'].buffer(distance)
        
        # Reproject back to the original CRS
        gdf_buffered = gdf_projected.to_crs(gdf.crs)
        
        return gdf_buffered



    ## union into one gdf

    def unary_union_polygons(gdf):
        # Combine all geometries into a single geometry
        unified_geometry = unary_union(gdf['geometry'])
        
        # Create a new GeoDataFrame with a single row containing the unified geometry
        combined_gdf = gpd.GeoDataFrame({'geometry': [unified_geometry]}, crs=gdf.crs)
        
        return combined_gdf
    
    boundary_buffered, boundary = set_location_boundary(place)
    guf = get_guf(place)
    residential_areas = get_residential_areas(boundary_buffered)

    guf_residential_gdf = join_geodataframes(guf, residential_areas)
    guf_residential_gdf = buffer_geometries_in_meters(guf_residential_gdf, 100)  # Buffer by 100 meters
    guf_residential_gdf = unary_union_polygons(guf_residential_gdf)

    return(guf_residential_gdf)



def process_maxspeeds(graph):
    """
    Process the 'maxspeed' attributes in the edges of the given graph.
    If 'maxspeed' is a list, only keep the first item. Otherwise, leave it as is.

    Parameters:
        graph (networkx.Graph): The input graph with edges containing 'maxspeed' attributes.

    Returns:
        networkx.Graph: The graph with processed 'maxspeed' attributes.
    """
    # Function to extract the first speed if maxspeed is a list
    def get_first_speed(maxspeed):
        if isinstance(maxspeed, list):  # Check if maxspeed is a list
            return maxspeed[0]  # Return the first item
        return maxspeed  # Otherwise, return as is

    # Iterate through all edges and process 'maxspeed'
    for u, v, data in graph.edges(data=True):
        if 'maxspeed' in data:
            data['maxspeed'] = get_first_speed(data['maxspeed'])  # Process and update 'maxspeed'

    return graph

def process_lists(graph):
    """
    Process the attributes in the edges of the given graph.
    If any attribute value is a list, only keep the first item. Otherwise, leave it as is.

    Parameters:
        graph (networkx.Graph): The input graph with edges containing attributes.

    Returns:
        networkx.Graph: The graph with processed attributes, where list attributes are reduced to their first item.
    """
    # Function to extract the first item from a list if the attribute is a list
    def get_first_item(attribute_value):
        if isinstance(attribute_value, list):  # Check if the attribute value is a list
            return attribute_value[0]  # Return the first item of the list
        return attribute_value  # Otherwise, return the value as is

    # Iterate through all edges and process their attributes
    for u, v, data in graph.edges(data=True):
        for attr, value in data.items():
            data[attr] = get_first_item(value)  # Process each attribute

    return graph
