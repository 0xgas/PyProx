#!/usr/bin/python3
# PyProx!

import sys
import argparse
import socket
import time
import threading

Verbose = False


class PyProx():
	
	def __init__(self, args):
		self.src_host = args.src_host
		self.src_port = args.src_port
		self.dst_host = args.dst_host
		self.dst_port = args.dst_port
		self.last_time = time.time()


		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	def run(self):
		log("i", "Listening connections on %s:%d" % (self.src_host, self.src_port))
		self.server.bind((self.src_host, self.src_port))
		self.server.listen(5)
		while True:
			client_data = self.server.accept()
			log("i", "New connection from %s:%d!" % (client_data[1][0], client_data[1][1]))
			t= threading.Thread(target=self.proxy_handle, args=(client_data,))
			t.setDaemon(True)
			t.start()


	def proxy_handle(self, client_data):
		(client,addr)=client_data
		self.remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.remote.connect((self.dst_host, self.dst_port))

		log("a", "Trying to get data from remote...")
		remote_buffer = self.recv_from(self.remote)
		if len(remote_buffer):
			hexdump(remote_buffer)
			log("i", "Sending %d bytes to client" % len(remote_buffer))
			client.send(remote_buffer)
		else:
			log("a", "No data from remote, listening client now...")
		while True:
			local_buffer = self.recv_from(client)
			
			if len(local_buffer):
				hexdump(local_buffer)
				log("i", "Received %d bytes from client" % len(local_buffer))
				try:
					self.remote.send(local_buffer)
				except BrokenPipeError:
					log("w", "Lost connection to remote, reconnecting...")
					self.remote.close()
					self.remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					self.remote.connect((self.dst_host, self.dst_port))
					self.remote.send(local_buffer)
				log("i", "Sent to remote")
			remote_buffer = self.recv_from(self.remote)
			if len(remote_buffer):
				hexdump(remote_buffer)
				log("i", "Received %d bytes from remote" % len(remote_buffer))
				client.send(remote_buffer)
				log("i", "Sent to client")

			if not len(local_buffer) and not len(remote_buffer) and (time.time() - self.last_time) > 40:
				self.close_conns(client)
				return

	def recv_from(self, sock, timeout=0.5):
		buf=b""
		if timeout is not None:
			sock.settimeout(timeout)
		try:
			while True:
				data = sock.recv(4096)
				if not len(data):
					break
				buf += data
				self.last_time = time.time()
		except:
			pass
		return buf

	def close_conns(self, client=None):
		if client is not None:
			client.close()
		self.remote.close()
		log("i", "No more data, closing connections")
		return 

def main():
	global Verbose
	args=parse_params()
	Verbose = args.verbose
	proxy = PyProx(args)
	proxy.run()
	return


def hexdump(src, length=16):
	result = []
	digits = 2
	for i in range(0, len(src), length):
		s = bytes(src[i:i+length])
		hexa = ' '.join(["%0*x" % (digits, x) for x in s])
		if len(hexa) < length*digits+(length-1):
			hexa= hexa + (" " * (length*digits+(length-1) - len(hexa)))
		text = ''.join(["%s" % chr(x) if 0x20 <= x < 0x7F else '.' for x in s])
		result.append("%08x  %-*s  |%s|" % (i, 9, hexa, text))
	print('\n'.join(result))

def parse_params():
	parser = argparse.ArgumentParser()
	parser.add_argument('-v','--verbose', help="Verbose mode", action="store_true")
	parser.add_argument('-6','--ipv6', help="Use ipv6 for remote host", action="store_true")
	parser.add_argument('-u','--udp', help="Use UDP proto (Not working yet)", action="store_true")
	parser.add_argument('src_host', help="src IP to bind", type=str)
	parser.add_argument('src_port', help="src PORT to bind", type=int)
	parser.add_argument('dst_host', help="dst IP to listen", type=str)
	parser.add_argument('dst_port', help="dst PORT to listen", type=int)

	return parser.parse_args()

def log(mode, msg):
	if Verbose:
		if mode == 'e': # Error
			sys.stdout.write("[\033[31mx\033[0m] ")
		if mode == 'i': # Info
			sys.stdout.write("[\033[32m*\033[0m] ")
		if mode == 'a': # Action
			sys.stdout.write("[\033[33m+\033[0m] ")
		if mode == 'w': # Warning
			sys.stdout.write("[\033[34m!\033[0m] ")
		sys.stdout.write(str(msg) + "\n")
		sys.stdout.flush()

if __name__=='__main__':
	main()
