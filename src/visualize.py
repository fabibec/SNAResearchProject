import os

import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap as Basemap
from dotenv import load_dotenv

load_dotenv()
data_path = os.environ.get("DATA_PATH")
red = "#EF3D59"
orange = "#E17A47"
yellow = "#EFC958"
green = "4AB19D"
blue = "#344E5C"

nodes = pd.read_csv(data_path + "/stations/processed/stations.csv")
edge_list = pd.read_csv(data_path + "/edges/connection_list.csv", index_col=False)


graph = nx.from_pandas_edgelist(edge_list, 'source', 'target',
                                edge_attr='connections', create_using=nx.DiGraph())

m = Basemap(
    projection='merc',
    llcrnrlon=5.75,
    llcrnrlat=47.25,
    urcrnrlon=15.5,
    urcrnrlat=55,
    lat_ts=0,
    resolution='l',
    suppress_ticks=True)

mx, my = m(nodes['longitude'].values, nodes['latitude'].values)
pos = {}
for count, elem in enumerate(nodes['name']):
    pos[elem] = (mx[count], my[count])

nx.draw_networkx_nodes(graph, pos, node_color=red, alpha=0.8, node_size=75)
nx.draw_networkx_edges(graph, pos, edge_color=blue, alpha=0.2, arrows=False)

m.drawcountries(linewidth=3)
m.drawstates(linewidth=0.2)
m.drawcoastlines(linewidth=3)
plt.tight_layout()
plt.savefig(data_path + "/map.png", format="png", dpi=300)

