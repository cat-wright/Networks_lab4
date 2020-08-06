#Compile and run using Python version 3.6.8 on the UNM linux machines
#An example of running this code: python3 Router.py 10.10.10.10 RouterA LSA/RouterA_LSA.csv
import sys
import socket
import time
import math
import select
import copy
import csv
#Included in this directory.  
import Packet
import Dijkstra

#start_router():  Opens a server socket to listen and receive messages and a client socket to send messages.  The server socket is opened on the global port number and the client is opened on the global port number plus 1.  For example, RouterB with simulated IP address "10.10.10.20" will have server port 8020 will, and server socket bound to ("localhost", 8020), and its client socket bound to ("localhost", 8011). Once sockets are initialized the infinite loop starts which firsts tries to read data from the server socket.  If there is an incoming message it handles it according to the message type.  If there is nothing to read it reads from the command line to handle broadcasting/dijkstras requests.  
def start_router():
	UDP_IP_Address = "localhost"
	global port_no, Dijkstra_has_run, table_cost, predecessors
	c_port_no = port_no + 1
	seqnum = 0
	Dijkstra_has_run = False

	#Starting server socket to receive messages
	try:
		UDP_ss = socket.socket(family = socket.AF_INET, type = socket.SOCK_DGRAM)
		UDP_ss.bind((UDP_IP_Address, port_no))
		UDP_ss.setblocking(0)
	except socket.error as err:
		print("Server socket failure with error ",err)

	#Starting client socket to send messages
	try:	
		UDP_cs = socket.socket(family = socket.AF_INET, type = socket.SOCK_DGRAM)
		UDP_cs.bind((UDP_IP_Address,c_port_no))
	except socket.error as err:
		print("Client socket failure with error ",err)

	#Initiate the router's log - creates the file and writes the header
	initiate_log()
	#Infinite loop to run simulation
	while True:
		try:
			data,addr = UDP_ss.recvfrom(1024)
			in_c_port = int(addr[1])
			p = Packet.frombytes(data)
			#If the packet type is a flood packet...
			if isinstance(p, Packet.FloodPack):
				if p.seq < seqnum:
					if DEBUG: print("duplicate packet found")
					write_to_log("flood",p.src,in_c_port,0,"No Message","Drop")
					continue
				seqnum = p.seq + 1
				if DEBUG: print("found viable flood packet with data" + p.payload)
				[recv_db, recv_ports] = parse_packet_load(p.payload)
				update_table(recv_db, "database")
				update_table(recv_ports, "ports_table")
				#reachable_ports contains all neighbor ports derived from the LSA
				for po in reachable_ports:
					UDP_cs.sendto(p.tobytes(), (UDP_IP_Address, po))
					write_to_log("flood",p.src,in_c_port,po,"No Message","Forward")
			#If the packet type is a Dijkstra broadcast...
			elif isinstance(p, Packet.DijkPack) and not p.dest:
				if DEBUG: print("found viable dijkstra broadcast packet with data" + p.payload)
				if Dijkstra_has_run == False:
					[table_cost, predecessors] = Dijkstra.dijkstra(database)
					rt = build_routing_table(table_cost, predecessors)
					Dijkstra_has_run == True
				[ports_to_send_to,_] = send_dijkstras(p.src)
				if len(ports_to_send_to) == 0:
					write_to_log("broadcast: Dijkstra", p.src, in_c_port, 0, p.payload, "Drop")
				for po in ports_to_send_to:
					UDP_cs.sendto(p.tobytes(), (UDP_IP_Address, po))
					write_to_log("broadcast: Dijkstra", p.src, in_c_port, po, p.payload, "Forward")
			#If the packet tye is a peer-to-peer Dijkstra request...
			elif isinstance(p, Packet.DijkPack) and p.dest:
				if DEBUG: print("found viable p2p dijkstra packet with data" + p.payload)
				if Dijkstra_has_run == False:
					[table_cost, predecessors] = Dijkstra.dijkstra(database)
					build_routing_table(table_cost, predecessors)
					Dijkstra_has_run == True
				if p.dest == IP_addr:
					print("Arrived!")
					write_to_log("p2p: Dijkstra", p.src, in_c_port, 0, p.payload, "Drop", p.dest)
				else:
					dest_port = p2p_dijkstra(p.src, p.dest)
					write_to_log("p2p: Dijkstra", p.src, in_c_port, dest_port, p.payload, "Forward", p.dest)
					UDP_cs.sendto(p.tobytes(), (UDP_IP_Address, dest_port))
			#Any unknown type of message will print the data read and contine
			else:
				print("Message: ",data)
				#UDP_ss.close()
				#UDP_cs.close()
				#sys.exit()
		#Occurs if there is no incoming data to read
		except socket.error:
			#Non-blocking way to read the command line
			while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
				line = sys.stdin.readline().rstrip()
				#broadcast,noDijkstra is a flood request.  Creates a new flood message and sets the appropriate sequence number.  Data included is the LSA split into a data structure containing neighbor cost and a data structure containing ports associated with each neighbor
				if line == "broadcast,noDijkstra":
					sendMe = Packet.FloodPack()
					sendMe.seq = seqnum
					sendMe.payload = compress_table(LSA_database) + ":" + compress_table(LSA_ports_table)
					sendMe.src = IP_addr
					for p in reachable_ports:
						UDP_cs.sendto(sendMe.tobytes(), (UDP_IP_Address, p))
					seqnum += 1
				#boradcast,withDijkstra is a broadcast along the spanning tree created by running Dijkstras and this router as the source.  If this router hasn't run Dijkstra's algorithm on the network yet it first runs it.  This router checks if it is the predecessor of any routers, and only sends to those routers.  
				elif line == "broadcast,withDijkstra":
					if Dijkstra_has_run == False:
						[table_cost, predecessors] = Dijkstra.dijkstra(database)
						rt = build_routing_table(table_cost, predecessors)
						Dijkstra_has_run == True
					[ports_to_send_to, sendMe] = send_dijkstras(IP_addr, new = True)
					if DEBUG: print(ports_to_send_to)
					for p in ports_to_send_to: 
						UDP_cs.sendto(sendMe.tobytes(), (UDP_IP_Address, p))
				#If the request is a peer-to-peer Dijkstra, it checks to see if Dijkstras needs to be run.  It creates a message with the destination set to the specified router and determines where to send it.  
				elif line.split(',')[0] == 'p2p' and line.split(',')[1] == 'Dijkstra':
					dest_IP = line.split(',')[2]
					if Dijkstra_has_run == False:
						[table_cost, predecessors] = Dijkstra.dijkstra(database)
						build_routing_table(table_cost, predecessors)
						Dijkstra_has_run == True
					dest_port = p2p_dijkstra(IP_addr, dest_IP)	
					sendMe = Packet.DijkPack()
					sendMe.payload = "Dijkstra at your service!"
					sendMe.src = IP_addr
					sendMe.dest = dest_IP
					UDP_cs.sendto(sendMe.tobytes(), (UDP_IP_Address, dest_port))	
				#Used in debugging to see the routers current knowledge of the graph topology
				elif line == "print tables":
					print_table(database)
					print_table(ports_table)

# This method takes the costs table and predecessors table which was computed by the
#      dijkstra algorithm. Using that information it formats and writes to a csv file
#      containing the routing table
def build_routing_table(costs, preds):
	routing_table = [["Destination", "Cost", "Next Hop Address" ]]
	my_idx = IP_to_index[IP_addr]
	for idx,cost in enumerate(costs[my_idx]):
		ip = "10.10.10." + str((idx+1)*10)
		our_idx = IP_to_index[IP_addr]
		dest = idx
		pred = predecessors[my_idx][dest]
		while not pred == my_idx:
			dest = pred
			pred = predecessors[my_idx][dest]
		neighbor_dest_IP = "10.10.10." + str((dest+1)*10)
		routing_table.append([ip, cost, neighbor_dest_IP])

	routing_table_file = "RT/"+router_name+"_rt.csv"
	with open(routing_table_file, "w", newline="") as rt_in:
		writer = csv.writer(rt_in)
		writer.writerows(routing_table)

# This method takes the source and destination IP address' from a peer-to-peer message
#		and calculates where to send the message. The returned port is the port of the 
#		router to send the message to 
def p2p_dijkstra(src_IP, dest_IP):
	try:
		num = dest_IP.split(".")[3]
		dest_idx = int((int(num) /10 ) - 1)
		src_idx = int((int(src_IP.split(".")[3])/10) - 1)
	except: 
		print("Not a valid IP for peer-to-peer destination!")
		return
	our_idx = IP_to_index[IP_addr]
	dest = dest_idx
	pred = predecessors[src_idx][dest]
	while not pred == our_idx:
		dest = pred
		pred = predecessors[src_idx][dest]
	
	neighbor_dest_IP = "10.10.10."+str((dest+1)*10)	
	dest_port = int(neighbor_dest_IP.split(".")[3]) + 8000
	return dest_port

# Writes to this router's log
#		msgtype: either "flood","broadcast: Dijkstra", or "p2p: Dijkstra" 
#		source: the IP of the router that created the packet
#		clientport_in: the port which the message was received from
#		serverport_out: the port which the message will be sending from
#		message: the message being sent.  "N/A" if a flood
#		f_or_d: "Forward" to specify the message was passed on, or "Drop" to specify the message stopped here
#		destination: Used in peer-to-peer communication to specify the destination router for the message.
def write_to_log(msgtype, source, clientport_in, serverport_out,message, f_or_d, destination="N/A"):
	#clientport_in will be an integer such as 8011 for RouterA
	in_IP = "10.10.10."+str(clientport_in-8001)
	in_idx = IP_to_index[in_IP]
	idx = IP_to_index[IP_addr]
	if not serverport_out == 0: 
		out_IP = "10.10.10."+str(serverport_out-8000)
		out_idx = IP_to_index[out_IP]
		out_port = ports_table[idx][out_idx]
	else: out_port = "N/A"
	in_port = ports_table[idx][in_idx]
	line = msgtype+', '+source+', '+str(in_port)+', '+destination+', '+str(out_port)+', '+message+', '+f_or_d+'\n'
	with open(logfile, "a+") as logfile_in:
		logfile_in.write(line)

# Initiates the log by creating the file and writing the header
def initiate_log():
	with open(logfile, "w") as logfile_in:
		line = "Message type, Source IP, In Port, Destination IP, Out Port, Message Content, Forward/Drop\n"
		logfile_in.write(line)

# Returns the ports for which the message should be forwarded to, and if specified the instanciated packet
#		src_IP: the source IP of the packet
#		new: whether a packet needs to be created or not
def send_dijkstras(src_IP, new = False):
	global predecessors
	Index_to_IP = dict()
	for ip in IP_to_index.keys():
		i = IP_to_index[ip]
		Index_to_IP[i] = ip

	if DEBUG: print("Index to IP",Index_to_IP)

	idx = IP_to_index[IP_addr]
	num = src_IP.split(".")[3]
	source_idx = int((int(num) /10 ) - 1)
	ports = list()
	sendMe = None
	for j, c in enumerate(predecessors[source_idx]):
		c = int(c)
		if (c == idx and not c == j):
			if DEBUG: print("Trying to append!")
			if DEBUG: print("j: ",j)
			destIP = Index_to_IP[j]
			destPort = 8000+int(destIP.split(".")[3])
			ports.append(destPort)
	if new:
		sendMe = Packet.DijkPack()
		sendMe.payload = "Dijkstra at your service!"
		sendMe.src = src_IP
	return [ports, sendMe]

# update database or ports table with new values
#       type - can either be 'database' or 'ports'
#       table - a two dimensional array containing new database or ports values
def update_table(table, type):
	global database, ports_table
	if type == "database": orig_table = database
	else: orig_table = ports_table
	for i, row in enumerate(table):
		for j, col in enumerate(row):
			if orig_table[i][j] == math.inf and not col == math.inf:
				orig_table[i][j] = table[i][j]

# Parses the command line, reading in the global variables:
#		IP_addr: the simulated IP address of the router (e.g. 10.10.10.10 for RouterA)
#		router_name: the simulated router name (e.g. RouterA)
#		filename: the file containing the link-state advertisement of the router.  All files are in the LSA/ directory with the name {router_name}_LSA.csv  
def parse_cline():
	global IP_addr, router_name, filename 
	IP_addr = sys.argv[1]
	router_name = sys.argv[2]
	filename = sys.argv[3]

# Import information from LSA .csv file into the LSA_database and LSA_ports_table, which contain neighbor cost and port information.   
def import_LSA():
	global filename, IP_to_index, database, ports_table, IP_addr, reachable_ports, LSA_database, LSA_ports_table
	reachable_ports = []
	with open(filename, 'r+') as infile:
		for line in infile:
			adverts = line.rstrip().split(',')
			add_IP_address_to_mapping(adverts[0])
			last_digits = adverts[0].split('.')[3]
			server_portno = 8000 + int(last_digits)
			reachable_ports.append(server_portno)
			src_idx = IP_to_index[IP_addr]
			dest_idx = IP_to_index[adverts[0]]
			database[src_idx][dest_idx] = int(adverts[2])
			database[dest_idx][src_idx] = int(adverts[2])
			ports_table[src_idx][dest_idx] = int(adverts[1])
	LSA_database = copy.deepcopy(database)
	LSA_ports_table = copy.deepcopy(ports_table)

#Parses the IP to get the right port number
def parse_ip():
	global IP_addr, port_no, IP_to_index
	index = IP_addr.split('.')[3]
	port_no = 8000 + int(index)
	# Add IP address to IP_to_index mapping
	add_IP_address_to_mapping(IP_addr)

# Creates a global adjacency matrix called "database" that stores the LSA and LSD network values
def create_database():
    global database
    database = [[math.inf] * 7 for _ in range(7)]
    for i in range(7): database[i][i] = 0
	
# Creates a global adjacency matrix called "ports_table" that stores the network port information
def create_ports_table():
    global ports_table
    ports_table =[[math.inf] * 7 for _ in range(7)]

# Takes a 2D array and returns a compressed table as a string with all the 0s removed
def compress_table(table):
	n = len(table)
	output = ""
	for i in range(n):
		for j in range(n):
			cell_value = table[i][j]
			if (cell_value < math.inf):
				output += str(cell_value)
			output += ","
		output += "."
	return output

# Converts packet_string into a table containing the database and ports
def parse_packet_load(packet_string):
	data = packet_string.split(":")
	db = uncompress_table(data[0])
	ports = uncompress_table(data[1])
	return [db, ports]

# Takes the compressed string table generated from the compress_table method
#       returns a 2D array of the original table
def uncompress_table(table_str):
	table = [[math.inf] * 7  for _ in range(7)]
	rows = table_str.split(".")
	for i, r in enumerate(rows):
		cols = r.split(",")
		for j, c in enumerate(cols):
			if (c != ""):
				table[i][j] = int(c)
	return table

#  Create a dictionary that maps IP addresses to an index value. The index value corresponds to
#         the row and column index of the IP address in the database and ports table
def create_IP_index_mapping():
	global IP_to_index
	global Index_to_IP
	IP_to_index = dict()
	Index_to_IP = dict()

# Add an IP address to the mapping that links IP addresses to an index value for the database and ports tables.
#        The new IP address takes the next available index value ( it increments the previous maximum index by 1).
def add_IP_address_to_mapping(IP):
	if IP in IP_to_index:
		return
	num = IP.split(".")[3]
	idx = int((int(num) /10 ) - 1)
	IP_to_index[IP] = idx

	Index_to_IP = dict()
	for ip in IP_to_index.keys():
		idx = IP_to_index[ip]
		Index_to_IP[idx] = ip

# Print table to console
def print_table(table):
	for row in table:
		print(row)

# Creates the database and ports_table from the LSA.  Creates the necessary mappings from IP's to index numbers of 
# 		routers within the data structures.  All are 6x6 2-d structures, such that Router A has index 0 and Router
#		G has index 6 (and all others in between).  Next it parses the command line and the IP.  Finally it designates
#		the log file associated with this router, and starts the router.  
def main():
	global DEBUG
	DEBUG = False
	create_database()
	create_ports_table()
	create_IP_index_mapping()
	parse_cline()
	parse_ip()
	import_LSA()
	global logfile
	logfile = "LOG/" + router_name + "_log.csv"
	start_router()

if __name__ == "__main__":
	main()
