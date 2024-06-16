library(igraph)
library(caret)

nodes <- read.csv("/home/fabian/Education/IT_4/sna/SNAResearchProject/data/stations/processed/stations.csv", header=T, as.is=T)
links <- read.csv("/home/fabian/Education/IT_4/sna/SNAResearchProject/data/edges/connection_list.csv", header=T, as.is=T)

head(nodes)
head(links);
nrow(nodes);

nrow(links);
#check if thre are repeated nodes
nrow(unique(links[,c("source", "target")]))

#build the network
net <- graph_from_data_frame(d=links, vertices=nodes, directed=T)

class(net)
net
plot(net, edge.arrow.size=.4)

#statistics
edge_density(net)

#Reciprocity
#The proportion of reciprocated ties (for a directed network).

reciprocity(net)
dyad_census(net) # Mutual, asymmetric, and nyll node pairs

#Transitivity

transitivity(net, type="global")  # net is treated as an undirected network
transitivity(net, type="local")

triad_census(net) # for directed networks

#Diameter
diameter(net, directed=T)
diam <- get_diameter(net, directed=T)
diam


#Node degrees

deg <- degree(net, mode="in")

hist(deg, breaks=1:vcount(net)-1, main="Histogram of node degree")

#6.6 Degree distribution
deg.dist <- degree_distribution(net, cumulative=F, mode="in")
plot( x=0:max(deg), y=1-deg.dist, pch=19, cex=1.2, col="orange",
      xlab="Degree", ylab="Frequency")

#VArious measure of centrality
degree(net, mode="in")
closeness(net, mode="in")
eigen_centrality(net, directed=T)
btw<- betweenness(net, directed=T)

dev.off()


#check top 5 countries
deg <- degree(net, mode="in")
sort(deg,decreasing = TRUE)[1:5]

#cluster
cfg <- cluster_fast_greedy(as.undirected(net))
igraph.options(plot.layout=layout.graphopt, vertex.size=1)
plot(cfg, as.undirected(net))
membership(cfg) # community membership for each node

#Analysis of homophily
#why are countries connected?
#Is it the coin?
assortativity_nominal(net, as.factor(V(net)$federalState), directed=T)
#Is it the EU membership?
assortativity_nominal(net, as.factor(V(net)$stationManagement), directed=T)
#Is it the type of language?
assortativity_nominal(net, as.factor(V(net)$operator), directed=T)


#Model Analysis
#Put all the information in one data frame

#predicting delay
deg <- degree(net, mode="in")
btw<- betweenness(net, directed=T)

#create a data frame
train_network <- cbind(degree=deg,btw=btw,clusters_id=membership(cfg),nodes)

#convert some variables in factors
europe$EU <- as.factor(europe$EU)
europe$Coin <- as.factor(europe$Coin)
europe$clusters_id <- as.factor(europe$clusters_id)

model0<-lm(Tourists~Land, data=europe)
summary(model0)

model1<-lm(Tourists~Population, data=europe)
summary(model1)


model2<-lm(Tourists~Population+EU, data=europe)
summary(model2)


model3<-lm(Tourists~Population+EU+degree, data=europe)
summary(model3)

#check if the model suffers from collinearity
car::vif(model3)

model4<-lm(Tourists~Population+EU+degree+btw, data=europe)
summary(model4)

#is model4 statistically better than model3
anova(model3,model4)

#Conclusions
#the btw centrality is strongly associated with number of visitors
#and it is a stronger indicators than population or degree centrality


#An additional analysis

#check cluster composition by some variables
table(europe$cl,europe$Language_group)
table(europe$cl,europe$EU)
table(europe$cl,europe$Coin)
