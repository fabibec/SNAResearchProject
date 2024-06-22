import os
import collections
import powerlaw
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpl_patches
from mpl_toolkits.basemap import Basemap as Basemap
from dotenv import load_dotenv

load_dotenv()
data_path = os.environ.get("DATA_PATH")
red = "#EF3D59"
orange = "#E17A47"
yellow = "#EFC958"
green = "#4AB19D"
blue = "#344E5C"

# Fetch data
nodes = pd.read_csv(data_path + "/stations/processed/stations.csv")
edge_list = pd.read_csv(data_path + "/edges/connection_list.csv", index_col=False)

m = Basemap(
    projection='merc',
    llcrnrlon=5.75,
    llcrnrlat=47.25,
    urcrnrlon=15.5,
    urcrnrlat=55,
    lat_ts=0,
    resolution='l',
    suppress_ticks=True)


def degree_distribution():
    plt.clf()
    graph = nx.from_pandas_edgelist(edge_list, 'source', 'target', create_using=nx.DiGraph())
    degree_sequence = sorted([d for d in dict(graph.degree()).values()], reverse=True)
    degree_count = collections.Counter(degree_sequence)

    deg, cnt = zip(*degree_count.items())
    fig, ax = plt.subplots()
    plt.bar(deg, cnt, width=0.80, color="#344E5C")

    plt.title("Degree Histogram")
    plt.ylabel("Count")
    plt.xlabel("Degree")

    labels = ['degree={0:.4g}'.format(sum(degree_sequence) / len(degree_sequence))]

    handles = [mpl_patches.Rectangle((0, 0), 1, 1, fc="white", ec="white",
                                     lw=0, alpha=0)] * 2

    ax.legend(handles, labels, loc='best',
              fancybox=True, framealpha=0.7,
              handlelength=0, handletextpad=0)
    plt.savefig(data_path + "/visualizations/degree_dist.png", dpi=600)


def german_map_visualization():
    plt.clf()
    graph = nx.from_pandas_edgelist(edge_list, 'source', 'target', create_using=nx.DiGraph())

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
    plt.savefig(data_path + "/visualizations/network.png", format="png", dpi=600)


def controlled_stations(station):
    plt.clf()
    nuernberg_stations = nodes[nodes["controlCenter"] == station]

    g = nx.Graph()
    for row in nuernberg_stations.iterrows():
        g.add_node(row[1]["name"], longitude=row[1]["longitude"], latitude=row[1]["latitude"])

    mx, my = m(nuernberg_stations['longitude'].values, nuernberg_stations['latitude'].values)
    pos = {}
    for count, elem in enumerate(nuernberg_stations['name']):
        pos[elem] = (mx[count], my[count])

    color_map = [red if node == station else green for node in g]
    nx.draw_networkx_nodes(g, pos, node_color=color_map, alpha=0.8, node_size=75)
    m.drawcountries(linewidth=3)
    m.drawstates(linewidth=0.2)
    m.drawcoastlines(linewidth=3)
    plt.tight_layout()
    formated_station = station.split(" ")[0]
    plt.savefig(data_path + f"/visualizations/{formated_station}_controlled_stations.png", format="png", dpi=600)
    plt.clf()


def power_law_fit():
    plt.clf()
    graph = nx.from_pandas_edgelist(edge_list, 'source', 'target', create_using=nx.DiGraph())

    # Data preparation
    degree_sequence = sorted([d for d in dict(graph.degree()).values()],
                             reverse=True)  # degree sequence sorted from the highest one
    degree_count = collections.Counter(degree_sequence)
    deg, cnt = zip(*degree_count.items())
    data = cnt

    # Power law fitting
    results = powerlaw.Fit(data)
    print("alpha", results.power_law.alpha)
    print("xmin", results.power_law.xmin)
    print("sigma", results.power_law.sigma)
    R, p = results.distribution_compare('power_law', 'lognormal')
    print(R, p)
    R, p = results.distribution_compare('power_law', 'exponential')
    print(R, p)

    # Visualizing
    fig = results.plot_ccdf(linewidth=3, label='Station Data', color=blue)
    plt.title("Power-Law Fit")
    results.power_law.plot_ccdf(ax=fig, color=red, linestyle='--', label='Power law fit')
    fig.set_ylabel("Count")
    fig.set_xlabel("Degree")
    handles, labels = fig.get_legend_handles_labels()
    fig.legend(handles, labels, loc=3)
    plt.savefig(data_path + '/visualizations/powerlaw_fit.png', bbox_inches='tight', dpi=600)


if __name__ == "__main__":
    '''Plot the degree distribution'''
    degree_distribution()

    '''Visualize the power law fit of the degree distribution'''
    power_law_fit()

    '''Visualize the stations that are controlled by a control center'''
    controlled_stations("Nürnberg Hbf")
    controlled_stations("Dortmund Hbf")

    '''Visualize the whole network on a german map'''
    german_map_visualization()

