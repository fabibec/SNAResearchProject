import os
import collections
import networkx as nx
import operator
import pandas as pd
from dotenv import load_dotenv

red = "#EF3D59"
orange = "#E17A47"
yellow = "#EFC958"
green = "#4AB19D"
blue = "#344E5C"

# Create Graph
load_dotenv()
data_path = os.environ.get("DATA_PATH")
fh = open(data_path + "/edges.csv", 'rb')
next(fh, None)
G = nx.read_edgelist(fh, delimiter=',', data=False, create_using=nx.DiGraph)
fh.close()


def size():
    print("Network Size")
    print("Number of nodes: ", len(G.nodes))
    print("Number of Links: ", len(G.edges))


def centrality_measures():
    print("Centrality measures")
    # Degree (in+out)
    print("degree_centrality")
    sorted_x = sorted(dict(G.degree()).items(), key=operator.itemgetter(1), reverse=True)
    a = nx.get_node_attributes(G, 'type')
    print(sorted_x[0:10])

    # Betweenness_centrality
    print("betweenness_centrality")
    Btw = nx.betweenness_centrality(G)
    sorted_x = sorted(Btw.items(), key=operator.itemgetter(1), reverse=True)
    print(sorted_x[:10])

    # Edge_betweenness_centrality
    print("edge_betweenness_centrality")
    Edg = nx.edge_betweenness_centrality(G)
    sorted_x = sorted(Edg.items(), key=operator.itemgetter(1), reverse=True)
    print(sorted_x[:10])

    # closeness_centrality
    print("closeness_centrality")
    Clo = nx.closeness_centrality(G)
    sorted_x = sorted(Clo.items(), key=operator.itemgetter(1), reverse=True)
    print(sorted_x[:10])

    # eigenvector centrality
    print("eigenvector_centrality")
    Eig = nx.eigenvector_centrality(G)
    sorted_x = sorted(Eig.items(), key=operator.itemgetter(1), reverse=True)
    print(sorted_x[:10])


def triads():
    print("Triad census")
    census = nx.triadic_census(G)
    census = sorted(census.items(), key=operator.itemgetter(1), reverse=True)
    print(census)


def assortativity():
    r = nx.degree_assortativity_coefficient(G)
    print(f"Assortativity: {r:.3f}")


def stats_by_station_type():
    nodes = pd.read_csv(data_path + "/nodes.csv", index_col=False)

    types = nodes.set_index('name').to_dict('index')
    nx.set_node_attributes(G, types)

    types = nx.get_node_attributes(G, 'type')

    res = collections.Counter(types.values())

    for v in res.keys():
        n = [x for x, y in G.nodes(data=True) if y['type'] == v]
        deg = nx.degree(G, n)
        deg_sum = 0
        for d in deg:
            _, num = d
            deg_sum += num
        platforms = 0
        l = [y for x, y in G.nodes(data=True) if y['type'] == v]
        for dct in l:
            platforms += dct['platforms']

        print(f"{v}:\n amount: {res[v]} \n percentage: {round( res[v] / len(G.nodes),2)}"
              f"\n avg_deg: {round(deg_sum / res[v],2)}\n avg_platforms: {round(platforms / res[v],2)}")


def print_attributes():
    # Stations with the most platforms
    print("Stations with the most platforms")
    nodes = pd.read_csv(data_path + "/nodes.csv", index_col=False)
    n = nodes[["name", "type", "platforms"]]
    n = n.sort_values(by='platforms', ascending=False)
    print(n.head(10))

    # Stations by operators
    print("Stations by operators")
    print(nodes["operator"].value_counts())

    # Get amount and percentage of Metropolitan train stations from these operators
    print("Amount and percentage of Metropolitan train stations")
    metropol = nodes[(nodes["type"] == "Metropolbahnhof")]
    bw = metropol[metropol["operator"] == "nahverkehrsgesellschaft-baden-wurttemberg-mbh"]
    mv = metropol[metropol["operator"] == "verkehrsgesellschaft-mecklenburg-vorpommern-mbh"]
    print(f"nahverkehrsgesellschaft-baden-wurttemberg-mbh:\n amount: {len(bw)}\n percentage: {round(len(bw) / len(metropol) * 100, 2)}")
    print(f"verkehrsgesellschaft-mecklenburg-vorpommern-mbh:\n amount: {len(mv)}\n percentage: {round(len(mv) / len(metropol) * 100, 2)}")

    # Get mean of average delay
    print("Mean  of average delay")
    print(nodes["avgDelayIn"].mean())


if __name__ == "__main__":
    '''General size of the network'''
    size()

    '''Various centrality measures'''
    centrality_measures()

    '''Print triads'''
    triads()

    '''Print assortativity'''
    assortativity()

    '''Stats for the three station types'''
    stats_by_station_type()

    '''Print various '''
    print_attributes()
