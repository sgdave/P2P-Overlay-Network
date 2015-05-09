import sys, json, time, socket, random
from pprint import pprint, pformat
from threading import Timer

T_HELLO = 10
PORT = 7653
CONF = {}
ADDR_S = ()
ADDR_R = ()

def load_config(config_file_name):
	with open(config_file_name) as config_file:
		data = json.load(config_file)
	pprint(data)
	return data
def load_socket(ip, port = PORT):
	print "Binding to %s:%s"%(ip, port)
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind((ip, port))
	return sock
def log(payload, addr = False):
	if not addr:
		addr = ADDR_S
		lmsg = "[localhost:%s]\t=> "%addr[1]
	else:
		lmsg = "[%s:%s]\t<= "%(addr[0], addr[1])
	print lmsg, json.dumps(payload)

def send_socket(message, type_str, ip = False, port = PORT):
	if not ip:
		if message['path']:
			ip = message['path'].pop(-1)
		else:
			print "ERROR: no ip or path provided"
			return False
	log("Sending %s to %s:%s"%(type_str, ip, port))
	payload = {'type': type_str, 'body': message}
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	payload_str = json.dumps(payload)
	sock.sendto(payload_str, (ip, port))
def send_forward(message, type_str = 'query'):
	neighbors = CONF['ip_neighbors']
	if not neighbors and type_str == 'query':
		log("Error: No more neighbors to transmit to. Dumping.")
		send_socket(message, 'dump')
	for target_ip in neighbors:
		if (not type_str == 'query') or not (ADDR_R and target_ip == ADDR_R[0]):
			send_socket(message, type_str, target_ip)

def handle_hello(message):
	pass
def handle_query(message):
	search_result = random.choice([True, False])
	if search_result == True:
		send_socket(message, 'reply')
	else:
		message['path'].append(ADDR_S[0])
		send_forward(message)
def handle_reply(message):
	if not message['path']:
		log("Success: Search complete.")
	else:
		send_socket(message, 'reply')
def handle_dump(message):
	if not message['path']:
		log("Error: Search failed.")
	else:
		send_socket(message, 'dump')
def handle_error(message):
	log("Error: Unrecognized payload type. Ignoring paylod.")

HANDLERS = {
	'hello': handle_hello,
	'query': handle_query,
	'reply': handle_reply,
	'dump' : handle_dump,
	'error': handle_error
}
def handle_rx(payload):
	payload_type = payload['type']
	if not payload_type in HANDLERS:
		payload_type = 'error'
	try:
		HANDLERS[payload_type](payload['body'])
	except Exception as e:
		log("ERROR")
		log(e)

def periodic_hello(lag, iter = -1):
	send_forward('hello', 'hello')
	if iter == 0:
		return True
	t = Timer(lag, periodic_hello, args=[lag, iter - 1])
	t.start()
	return t

def main():
	global CONF, ADDR_S, ADDR_R
	cfn = sys.argv[1] if len(sys.argv) == 2 else 'config.json'
	CONF = load_config(cfn)
	sock = load_socket(CONF['ip_self'])
	ADDR_S = (CONF['ip_self'], PORT)
	
	if CONF['router_id'] == 'R2':
		send_forward({'path': [ADDR_S[0]]}, 'query')
	
	periodic_hello(T_HELLO)

	while True:
		data, addr = sock.recvfrom(1024)
		ADDR_R = addr
		payload = json.loads(data)
		log(payload, addr)
		handle_rx(payload)

main()