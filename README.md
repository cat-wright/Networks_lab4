# Link-state Routing Simulator
This lab demonstrates how a network works at the level of Network and Link state Layers. In this project, we have created a network architecture based on a given topology of links, their connections and the cost of the paths between them. Using this structure we implemented a simple flooding algorithm by which nodes broadcast to all available links while avoiding an infinite "storm". We also implemented a more sophisticated broadcast algorithm performed using Dijkstra's algorithm which finds the single-source shortest paths. Finally we performed a peer to peer sending of messages using routing tables formed by the Dijkstra's algorithm. All the logs of the three types of message passing were recorded in the individual tables of the routers.

## How to run:
### Clone the code
1. `git clone git@lobogit.unm.edu:fall19group4/lab4.git`
2. `cd lab4`

### Running the servers aka routers
3. Open 7 terminals
4. Run `python3 Router.py 10.10.10.10 RouterA LSA/RouterA_LSA.csv` in one
5. Change the name, IP, and LSA file for other routers and execute the above script in the other terminals as mentioned in the lab4 pdf 

### Initiate the operations  
6. Type `broadcast,noDijkstra` under each terminal
7. Type `broadcast,withDijkstra` to generate the Routing table
8. Use `p2p,Dijkstra,10.10.10.60` for your desired destination.

## Components:

There are 6 components in this lab, where 3 files are python scripts namely Router.py, Packet.py and Dijkstra.py and the other 3 are collections of csv files named LSA, RT, LOG.

### Router.py
The `Router.py` file creates a router by starting a server that can send and receive packets from other routers. When initially starting up, the router reads from its LSA file, and stores information about its neighbors.  It creates outgoing sockets via a one-to-one mapping from the simulated router IP to an actual port on the local host. The server also listens for input from the user via stdin. The router has three different routing algorithms, and can send and receive three corresponding packets for:
 * Flooding / Broadcast without Dijkstra
 * Broadcast with Dijkstra
 * Peer to Peer

#### Flooding/ Broadcast, without Dijkstra

After a user enters `broadcast,noDijkstra`, the router sends a packet to each of its neighbors with a sequence number. All routers are initialized to a sequence number of 0, but when a router initializes a broadcast, it increments its sequence number and sends the new sequence number in the packet to its neighbors. If a router receives a packet from its neighbor, it first checks the sequence number. If the sequence number in the packet is bigger than the one it has stored locally, it updates its local sequence number with the new sequence number, and then sends the packet on to the rest of its neighbors. If a router receives a packet with the same sequence number it has stored locally, it recognizes this packet as a duplicate of one it received before, and it drops the packet without sending.

#### Broadcast with Dijkstra 

After a user enters `broadcast,withDijkstra`, the router then uses its database table to build up a routing table containing the minimum cost for every router to get to every other node. By using Dijkstra's algorithm, the router essentially builds up a minimum cost spanning tree between it and the other nodes. After building up a spanning tree, the router then sends a packet to all of its neighbors in the spanning tree. The packet contains the IP address of the router that initiated the broadcast, along with a message. Dijkstra broadcast packets are differentiated from p2p packets by their destination, which is set to None.

Routers that receive a Dijkstra broadcast message first check to see if they have computed their own routing table. If not, then they use Dijkstra's algorithm to build their own table containing the minimum cost spanning tree for every router to get to every other node. They then check the packet for the source IP of the message in order to identify the source router's minimum spanning tree. The router then looks for its neighbors in the minimum spanning tree, and sends the packets to those neighbor ports.

#### Peer to Peer 

After a user enters `p2p,Dijkstra,{destination IP}`, the router uses its database table to build up a routing table similar to the **Broadcast with Dijkstra** protocol. After calculating a minimum spanning tree between the source router and the destination, the source router then sends a packet to its immediate neighbor that is on the minimum path between the source and the destination. The packet contains the source IP, and the destination IP. 

If a router receives a peer to peer message, it checks its own routing table to identify the minimum cost path between the source and destination node. If it has not generated a routing table yet, it will create one using Dijkstra's algorithm on information from the database table. After identifying the minimum cost path between the source IP and the destination IP, the router sends the packet to its neighbor that is on the minimum cost path. Once a router receives a packet that has itself as the destination, then we know that the packet has arrived.

### Packet.py

This file consists of the declarations of the packet structures sent between routers, as well as the necessary wrappers to serialize them into a bit stream for transmission.  The packets are structured as python classes, allowing for our code to be extended to other types of messages.  Different subclasses of packets were intended to be used for different routing algorithms, with added data fields for the elements required for each packet to propagate correctly.  The serialization is accomplished through the Python built-in library Pickle, which can serialize arbitrary objects into relatively small bit strings.

### Dijkstra.py

This python script consists of the logic to calculate the shortest paths from a source to a destination. The file is been imported inside Router.py. The Dijkstra function takes a graph with weights of each link in the adjacency matrix format and outputs two matrices with the updated shortest path from each router to each router and another matrix of all the predecessor router nodes which comes in the path for the shortest path.

### LSA files

The LSA files are a standard csv file containing information about the router's neighbors. There are 3 columns: Neighbor IP, Port, Cost. The Neighbor IP contains the IP address of the router's neighbor in the network. The Port column contains the port through which the router communicates with that neighbor. The Cost column contains information about the cost it would take to send a packet to that neighbor. One such file is loaded when each router is first created. 

### RT files

The RT files contain routing tables for each of the routers. The routing tables are generated the first time a router sends a Dijkstra broadcast or peer to peer packet. The routing table is computed using Dijkstra's algorithm to find the minimum cost between a router and all the other nodes in the network. As a csv file, the routing table has three columns: Destination, Cost, and Next Hop Address. The Destination column contains the IP addresses of the other routers in the network, and the Cost column contains information about the total cost to send a packet to that node. The Next Hop Address column contains the neighbor on the min-cost path to get to the destination node. This is the node that will receive the packet in a peer to peer message from the source address to the destination. 

### LOG files

These are the files that are associated with each router which consist of the logs of each and every message passed and received by every router whether it was during flooding, broadcasting via Dijkstra or during peer to peer. The fields used here are `Message type, Source IP, In Port, Destination IP, Out Port, Message Content, Forward/Drop` whose values are updated every time a packet is passed through them or when the paths are updated.

## Contributions

Cat - Set up the server on the router with working sockets and listening for user input. Worked on flooding, broadcast with Dijkstra, and peer to peer, and logging. 

Carolyn - Set up the database and ports table, along with IP mappings. Worked on the Dijkstra broadcast and peer to peer, and writing the routing table to a file. 

Nitin - Wrote the Dijkstra algorithm to find the shortest path from every router to every other router. Worked on Dijkstra broadcast and peer to peer.

Thomas - Wrote the Packet classes and worked on flooding, peer to peer, and logging.  Helped with debugging and algorithm implementation.
