#!/usr/bin/python3
# PyProx! Simple network proxy to analyse what is passing between you and your target.

import sys
import asyncio
import socket
import fcntl
import struct
import argparse

Verbose 	= False
Output		= 'canon'


class PyProxLocal(asyncio.Protocol):
	LocalBuffer = b""
	
	def __init__(self, remote):
		self.remote = remote
		self.remote_up = False
		
	def data_manip(self, data):
		# Manipulate data when it leaves
		return data

	def connection_made(self, transport):
		self.peername = transport.get_extra_info('peername')
		log("a", "New connection from local - {}".format(self.peername))
		transport.pause_reading()
		self.transport = transport
		asyncio.ensure_future(self.proxy_out_connect()).add_done_callback(self.remote_ready)
	
	def remote_ready(self, *args):
		self.remote_up = True
		if len(self.LocalBuffer) > 0:
			self.transport_remote.write(self.LocalBuffer)
			LocalBuffer = b""

	def connection_lost(self, ex):
		log("w", "Connection lost from local - {}".format(self.peername))
		self.transport.close()

	def data_received(self, data):
		global LocalBuffer
		print()
		log("i", "Received {} bytes from local".format(len(data)))
		hexdump(data, '>')
		data=self.data_manip(data)
		if not self.remote_up:
			self.LocalBuffer+=data
		else:
			self.transport_remote.write(data)

	async def proxy_out_connect(self):
		loop = asyncio.get_event_loop()
		self.transport_remote, proxy_remote = await loop.create_connection(PyProxRemote, self.remote[0], self.remote[1])
		proxy_remote.transport_local = self.transport


class PyProxRemote(asyncio.Protocol):
	
	def data_manip(self, data):
		# Manipulate data when it arrives
		return data

	def connection_made(self, transport):
		self.peername = transport.get_extra_info('peername')
		log("a", "Connection made to remote {}".format(self.peername))
		self.transport = transport

	def connection_lost(self, ex):
		log("w", "Connection lost to remote {}".format(self.peername))
		self.transport.close()

	def data_received(self, data):
		global RemoteBuffer
		print()
		log("i", "Received {} bytes from remote".format(len(data)))
		hexdump(data, '<')
		data=self.data_manip(data)
		self.transport_local.write(data)
	
def parse_params():
	parser = argparse.ArgumentParser()
	
	parser.add_argument('LPort', help="Local port to bind", type=int)
	parser.add_argument('RHost', help="Remote host to connect", type=str)
	parser.add_argument('RPort', help="Remote port to connect", type=int)
	parser.add_argument('-I', '--interface', help="Interface to bind to (default: lo)", required=False, default="lo")
	parser.add_argument('-o', '--output', help="Output type (Hexadecimal, Ascii, Canonical)", choices=['hex', 'ascii', 'canon'], required=False, default='canon')
	parser.add_argument('-v', '--verbose', help="Verbose mode", action="store_true", required=False)
	return parser.parse_args()


def log(mode, msg):
	output=sys.stdout
	if Verbose:
		if mode == 'i': # Info
			output.write("[\033[32m*\033[0m] ")
		if mode == 'a': # Action
			output.write("[\033[33m+\033[0m] ")
		if mode == 'w': # Warning
			output.write("[\033[34m!\033[0m] ")
	elif mode == 'e':
		output=sys.stderr
		output.write("[\033[31mx\033[0m] ")
	else:
		return
	output.write(str(msg) + "\n")
	output.flush()


def hexdump(src, origin, length=16):
	global Output
	result = []
	digits = 2

	if origin == '<':
		origin='\033[33m<'
	elif origin == '>':
		origin='\033[32m>'
	else:
		raise ValueError("Bad origin")
	
	if Output == 'ascii':
		length*=4

	for i in range(0, len(src), length):
		s = bytes(src[i:i+length])

		hexa = ' '.join(["%0*x" % (digits, x) for x in s])
		if len(hexa) < length*digits+(length-1):
			hexa= hexa + (" " * (length*digits+(length-1) - len(hexa)))

		text = ''.join(["%s" % chr(x) if 0x20 <= x < 0x7F else '.' for x in s])
		if len(text) < length:
			text = text + (" " *(length - len(text)))

		if Output == 'canon':
			result.append("%s %08x  %-*s  |%s|" % (origin, i, int(length/2), hexa, text))
		elif Output == 'hex':
			result.append("%s %08x  %-*s" % (origin, i, length, hexa))
		elif Output == 'ascii':
			result.append("%s |%s|" % (origin, text))
		else:
			raise ValueError("Wrong output")
			
	print('\n'.join(result) + '\033[0m')


def if2ip(ifname):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	ip=socket.inet_ntoa(fcntl.ioctl(
		s.fileno(),
		0x8915,
		struct.pack('256s', bytes(ifname[:15], 'utf-8'))
	)[20:24])
	s.close()
	return ip


def main():
	global Verbose, Output

	loop = asyncio.get_event_loop()

	args = parse_params()
	if args.verbose:
		Verbose = True
	Output = args.output
	try:
		args.LHost=if2ip(args.interface)
	except Exception as e:
		log('e', "Invalid interface '{}'".format(args.interface))
		log('e', e)
		return

	coro = loop.create_server(lambda: PyProxLocal((args.RHost, args.RPort)), args.LHost, args.LPort)
	server = loop.run_until_complete(coro)
	try:
		loop.run_forever()
	except KeyboardInterrupt:
		pass
	except Exception as e:
		log("e", "Error during event_loop execution")
		log("e", e)
	finally:
		log("i", "Closing pyProx")
		server.close()
		loop.close()


if __name__=='__main__':
	main()

