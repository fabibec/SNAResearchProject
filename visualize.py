import os

import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap as Basemap
from dotenv import load_dotenv

load_dotenv()
data_path = os.environ.get("DATA_PATH")

graph = nx.from_pandas_edgelist(data_path + "/edges/connection_list.csv", source="source", target="target")
plt.figure(figsize=(10, 9))
nx.draw_networkx(graph)
plt.show()
