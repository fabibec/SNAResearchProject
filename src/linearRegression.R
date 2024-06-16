library(igraph)
library(caret)

nodes <- read.csv("/home/fabian/Education/IT_4/sna/SNAResearchProject/data/stations/processed/stations.csv", header=T, as.is=T)
links <- read.csv("/home/fabian/Education/IT_4/sna/SNAResearchProject/data/edges/connection_list.csv", header=T, as.is=T)

# build the network
net <- graph_from_data_frame(d=links, vertices=nodes, directed=T)
edge_density(net)

cl <- closeness(net, mode="all")
degI <- degree(net, mode="in")
degO <- degree(net, mode="out")
degIO <- degree(net, mode="all")
btw<- betweenness(net, directed=T)

# create a data frame for nodes
train_network <- cbind(btw=btw,nodes, cl=cl)

# convert some variables in factors
train_network$federalState <- as.factor(train_network$federalState)
train_network$segment <- as.factor(train_network$segment)
train_network$controlCenter <- as.factor(train_network$controlCenter)
train_network$type <- as.factor(train_network$type)

# Does the deplay depend on the number of plattforms
model0<-lm(delay~platforms, data=train_network)
summary(model0)

# Does the deplay depend on the type of station
model1<-lm(delay~type, data=train_network)
summary(model1)

# Does the deplay depend on the type of station
model2<-lm(punctuality~cl, data=train_network)
summary(model2)

#check if the model suffers from collinearity
car::vif(model2)

#is model4 statistically better than model3
anova(model0,model2)

# Does the deplay depend on the number of plattforms
model4<-lm(punctuality+handledTrains, data=train_network)
summary(model4)



edge_network <- cbind(links)
model3<-lm(avgDelay~connections+maxDelay, data=edge_network)
summary(model3)
car::vif(model3)