library(igraph)
library(caret)

nodes <- read.csv("/home/fabian/Education/IT_4/sna/SNAResearchProject/data/nodes.csv", header=T, as.is=T)
links <- read.csv("/home/fabian/Education/IT_4/sna/SNAResearchProject/data/edges.csv", header=T, as.is=T)

head(nodes)
head(links);
nrow(nodes);
nrow(links);

# check if thre are repeated nodes
nrow(unique(links[,c("source", "target")]))

# build the network
net <- graph_from_data_frame(d=links, vertices=nodes, directed=T)

# Edge Density
edge_density(net)

# Reciprocity & dyad_census
reciprocity(net)
dyad_census(net)

triad_census(net)

#Diameter
diameter(net, directed=T)
diam <- get_diameter(net, directed=T)
diam
