library(igraph)
library(caret)
library(olsrr)

nodes <- read.csv("/home/fabian/Education/IT_4/sna/SNAResearchProject/data/nodes.csv", header=T, as.is=T)
links <- read.csv("/home/fabian/Education/IT_4/sna/SNAResearchProject/data/edges.csv", header=T, as.is=T)

# build the network and calculate centrality measures
net <- graph_from_data_frame(d=links, vertices=nodes, directed=T)

cl <- closeness(net, mode="all")
degI <- degree(net, mode="in")
degO <- degree(net, mode="out")
deg <- degree(net, mode="all")
btw <- betweenness(net, directed=T)
eig <- eigen_centrality(net, directed=T)
e_btw <- edge_betweenness(net, directed = T)


# create a data frame for nodes
trains <- cbind(nodes, btw=btw, degI=degI, degO=degO, cl=cl, eig=eig)

# create a data frame for edges
edges <- cbind(links, btw = e_btw)

# convert some variables in factors
trains$federalState <- as.factor(trains$federalState)
trains$segment <- as.factor(trains$segment)
trains$controlCenter <- as.factor(trains$controlCenter)
trains$type <- as.factor(trains$type)

# check the influence of centrality measures on avgDelay <- degree
modelDegI <-lm(avgDelayIn ~ deg, data = trains)
summary(modelDegI)
ols_plot_resid_fit(modelDegI)

modelDegI <-lm(avgDelayIn ~ degI + numTrainsIn, data = trains)
summary(modelDegI)
car::vif(modelDegI)
ols_plot_resid_fit(modelDegI)

# check the influence of centrality measures on stdDevIn <- degree
modelDegO <-lm(stdDevOut ~ degI, data = trains)
summary(modelDegO)
ols_plot_resid_fit(modelDegO)

# check the influence of centrality measures on avgDelayIn <- betweeness
modelBtwI <-lm(avgDelayIn ~ btw, data = trains)
summary(modelBtwI)
ols_plot_resid_fit(modelBtwI)

# check the influence of centrality measures on stdDev <- betweeness
modelBtwI <-lm(stdDevIn ~ btw, data = trains)
summary(modelBtwI)
ols_plot_resid_fit(modelBtwI)

# Check edge betweenness
modelEdgeBtw <- lm(avgDelay ~ btw, data = edges)
summary(modelEdgeBtw)

# check the influence of centrality measures on avgDelay <- closeness
modelDegI <-lm(avgDelayIn ~ cl, data = trains)
summary(modelDegI)
ols_plot_resid_fit(modelDegI)

# check the influence of centrality measures on stdDev <- closeness
modelDegI <-lm(stdDevIn ~ cl, data = trains)
summary(modelDegI)
ols_plot_resid_fit(modelDegI)

# try to combine centrality measures
modelWholeCen <- lm(avgDelayIn ~ cl + btw+ degI, data = trains)
summary(modelWholeCen )
ols_step_all_possible(modelWholeCen)
ols_plot_resid_fit(modelWholeCen)
car::vif(modelWholeCen)

#---------------------

# check the influence of the number of platforms on delay
modelPlattDel <- lm(avgDelayIn ~ platforms, data = trains)
summary(modelPlattDel)
ols_plot_resid_fit(modelPlattDel)

modelPlattstd <- lm(stdDevIn ~ platforms, data = trains)
summary(modelPlattstd)
ols_plot_resid_fit(modelPlattstd)

# check the influence of the federalState on delay
modelStateDel <- lm(avgDelayIn ~ federalState, data = trains)
summary(modelStateDel)
ols_plot_resid_fit(modelStateDel)

# check the influence of the type of station on delay
modelTypeDel <- lm(avgDelayIn ~ type, data = trains)
summary(modelTypeDel)
ols_plot_resid_fit(modelTypeDel)

# check the influence of the number of trains on delay
modelTypeDel <- lm(avgDelayIn ~ operator, data = trains)
summary(modelTypeDel)
ols_plot_resid_fit(modelTypeDel)

# check the influence of the control center on delay
modelTypeDel <- lm(avgDelayIn ~ numTrainsIn, data = trains)
summary(modelTypeDel)
ols_plot_resid_fit(modelTypeDel)

# check if you can combine the models
modelWholeMeta <- lm(avgDelayIn ~ controlCenter + federalState +  platforms + type + numTrainsIn, data = trains)
car::vif(modelWholeMeta)
summary(modelWholeMeta )
ols_step_all_possible(modelWholeMeta )

# inspect the best model
modelMetaBest <- lm(avgDelayIn ~ controlCenter + federalState + type + numTrainsIn, data = trains)
summary(modelMetaBest)
ols_plot_resid_fit(modelMetaBest)
