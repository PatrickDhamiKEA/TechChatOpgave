import socket
from configparser import ConfigParser
import threading
import time
import re

your_ip = socket.gethostbyname(socket.gethostname())

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (your_ip, 5500)

sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address2 = (your_ip, 5501)

counter = 0

# Sat til True i stedet for False, så besked while loopet vil starte med at køre
# indtil max packages er nået
handshake_check = True
parser = ConfigParser()
parser.read('opt.conf')
char_encoding = "utf-8"
bufsize = 1024


def check_for_shutdown():
    while True:
        enc_hb_data, hb_server = sock2.recvfrom(bufsize)
        hb_data = enc_hb_data.decode(char_encoding)
        if 'con-res 0xFE' in hb_data:
            print('shutting down')
            send_hb = sock2.sendto('con-res 0xFF'.encode(char_encoding), server_address2)
            sock2.close()
            sock.close()


def heartbeat(delay, data):
    while True:
        send_hb = sock2.sendto(data.encode(char_encoding), server_address2)
        time.sleep(delay)


try:
    syn = 'com-' + str(counter) + ' ' + your_ip
    sent_syn = sock.sendto(syn.encode(char_encoding), server_address)
    enc_syn_ack, server = sock.recvfrom(bufsize)
    syn_ack = enc_syn_ack.decode(char_encoding)
    line_split = syn_ack.find('0')
    received_ip = syn_ack[syn_ack.index(' ') + (line_split+4):]
    if "com-0 accept" in syn_ack and socket.inet_aton(received_ip):
        ack = 'com-' + str(counter) + ' accept'
        sent_ack = sock.sendto(ack.encode(char_encoding), server_address)
        handshake_check = True
        if parser.get('setting', 'KeepALive') == 'True':
            delay_time = 10
            t = threading.Thread(target=heartbeat, name='con-h 0x00', args=(delay_time, 'con-h 0x00'))
            t.start()
            t2 = threading.Thread(target=check_for_shutdown)
            t2.start()

finally:
    if not handshake_check:
        print('closing socket')
        sock.close()

while handshake_check:
    message_input = "hello"
    msg = 'msg-' + str(counter) + '=' + message_input
    sent_msg = sock.sendto(msg.encode(char_encoding), server_address)
    enc_res, server = sock.recvfrom(bufsize)
    res = enc_res.decode(char_encoding)

    pre_count = int(re.search('res-(.*)=', res).group(1))
    counter = pre_count + 1
    if counter - pre_count == 1 and 'res-' in res:
        received_message = res[res.index('=') + 1:]
        print(received_message)
