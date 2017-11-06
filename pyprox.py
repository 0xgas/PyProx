#!/usr/bin/python3
# PyProx! Simple network proxy to analyse what is passing between you and your target.

import sys
import asyncio
import logging
import argparse

Verbose = False
LocalBuffer = b""

class PyProxLocal(asyncio.Protocol):
	
	def __init__(self, remote):
		self.remote = remote
		self.remote_up = False

	def connection_made(self, transport):
		self.peername = transport.get_extra_info('peername')
		log("a", "New connection from local - {}".format(self.peername))
		self.transport = transport
		asyncio.ensure_future(self.proxy_out_connect()).add_done_callback(self.remote_ready)
	
	def remote_ready(self, *args):
		global LocalBuffer
		self.remote_up = True
		if len(LocalBuffer) > 0:
			self.transport_remote.write(LocalBuffer)
			LocalBuffer = b""

	def connection_lost(self, ex):
		log("w", "Connection lost from local - {} ({})".format(self.peername, ex))
		self.transport.close()

	def data_received(self, data):
		global LocalBuffer
		log("i", "Received {} bytes from local".format(len(data)))
		hexdump(">", data)
		if not self.remote_up:
			LocalBuffer+=data
		else:
			self.transport_remote.write(data)

	def eof_received(self):
		pass

	async def proxy_out_connect(self):
		loop = asyncio.get_event_loop()
		self.transport_remote, proxy_remote = await loop.create_connection(PyProxRemote, self.remote[0], self.remote[1])
		proxy_remote.transport_local = self.transport


class PyProxRemote(asyncio.Protocol):
	
	def connection_made(self, transport):
		self.peername = transport.get_extra_info('peername')
		log("a", "Connection made to remote {}".format(self.peername))
		self.transport = transport

	def connection_lost(self, ex):
		log("w", "Connection lost to remote {} ({})".format(self.peername, ex))
		self.transport.close()

	def data_received(self, data):
		global RemoteBuffer
		log("i", "Received {} bytes from remote".format(len(data)))
		hexdump("<", data)
		self.transport_local.write(data)
	
	def eof_received(self):
		pass
	
def parse_params():
	parser = argparse.ArgumentParser()
	
	parser.add_argument('-v', '--verbose', help="Verbose mode", action="store_true", required=False)
	parser.add_argument('src_host', help="src IP to bind", type=str)
	parser.add_argument('src_port', help="src PORT to bind", type=int)
	parser.add_argument('dst_host', help="dst IP to listen", type=str)
	parser.add_argument('dst_port', help="dst PORT to listen", type=int)
	return parser.parse_args()


# logs on stderr, so redirecting stdout to a file only gets you the hexdump, which is cool imo
def log(mode, msg):
	if Verbose:
		if mode == 'e': # Error
			sys.stderr.write("[\033[31mx\033[0m] ")
		if mode == 'i': # Info
			sys.stderr.write("[\033[32m*\033[0m] ")
		if mode == 'a': # Action
			sys.stderr.write("[\033[33m+\033[0m] ")
		if mode == 'w': # Warning
			sys.stderr.write("[\033[34m!\033[0m] ")
		sys.stderr.write(str(msg) + "\n")
		sys.stderr.flush()


def hexdump(origin, src, length=16):
	result = []
	digits = 2
	print()
	for i in range(0, len(src), length):
		s = bytes(src[i:i+length])
		hexa = ' '.join(["%0*x" % (digits, x) for x in s])
		if len(hexa) < length*digits+(length-1):
			hexa= hexa + (" " * (length*digits+(length-1) - len(hexa)))
		text = ''.join(["%s" % chr(x) if 0x20 <= x < 0x7F else '.' for x in s])
		if len(text) < length:
			text = text + (" " *(length - len(text)))
		result.append("%s %08x  %-*s  |%s|" % (origin, i, 9, hexa, text))
	print('\n'.join(result))


def main():
	global Verbose
	logging.basicConfig(
			level=logging.DEBUG,
			format='%(name)s: %(message)s',
			stream=sys.stderr,
	)
	logR = logging.getLogger('main')
	loop = asyncio.get_event_loop()

	args = parse_params()
	if args.verbose:
		Verbose = True
	coro = loop.create_server(lambda: PyProxLocal((args.dst_host, args.dst_port)), args.src_host, args.src_port)
	server = loop.run_until_complete(coro)
	try:
		loop.run_forever()
	except KeyboardInterrupt:
		pass
	finally:
		log("i", "Closing pyProx")
		server.close()
		loop.close()


if __name__=='__main__':
	main()

