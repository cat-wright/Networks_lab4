#Uses Dijkstra's minimum cost algorithm to calculate a minimum-cost spanning tree from each node to reach every other node within the graph. 
import sys
import math

def minDistance(dist, sptSet, V):
    
    min = sys.maxsize

    for v in range(V):
        if dist[v] < min and sptSet[v] == False:
            min = dist[v]
            min_index = v

    return min_index

def dijkstra(graph):
    V = len(graph)

    cost = []
    pred = [] 
    
    for i in range(V):
        src = i
    
        dist = [sys.maxsize] * V
        dist[src] = 0
        sptSet = [False] * V
        parent = [sys.maxsize] * V
        
        for _ in range(V):
            u = minDistance(dist, sptSet, V)
            sptSet[u] = True

            for v in range(V):
                if graph[u][v] > 0 and  sptSet[v] == False and dist[v] > dist[u] + graph[u][v]:
                    dist[v] = dist[u] + graph[u][v]
                    parent[v] = u
                    
        cost.append(dist)
        pred.append(parent)

    for i in range(V):
        pred[i][i] = i
        
    return cost, pred

