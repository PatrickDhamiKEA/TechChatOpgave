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
handshake_check = False
parser = ConfigParser()
parser.read('opt.conf')
char_encoding = "utf-8"
bufsize = 1024


# funktion der kører på seperat tråd til at undersøge om der er sendt en
# shutdown besked fra serveren, pga. manglende heartbeat
def check_for_shutdown():
    while True:
        enc_hb_data, hb_server = sock2.recvfrom(bufsize)
        hb_data = enc_hb_data.decode(char_encoding)
        # Hvis true, sender den en besked tilbage til serveren, og vil lukke de to sockets
        if 'con-res 0xFE' in hb_data:
            print('shutting down')
            send_hb = sock2.sendto('con-res 0xFF'.encode(char_encoding), server_address2)
            sock2.close()
            sock.close()


def heartbeat(delay, data):
    while True:
        # sender heartbeat data fra t trådens argumenter
        send_hb = sock2.sendto(data.encode(char_encoding), server_address2)
        # hvor lang tid heartbeat funktionen skal vente med at gensende
        time.sleep(delay)


try:
    # sender syn når clienten tænder
    syn = 'com-' + str(counter) + ' ' + your_ip
    sent_syn = sock.sendto(syn.encode(char_encoding), server_address)
    # modtager synack fra server
    enc_syn_ack, server = sock.recvfrom(bufsize)
    syn_ack = enc_syn_ack.decode(char_encoding)
    line_split = syn_ack.find('0')
    # finder serverens IP i synack
    received_ip = syn_ack[syn_ack.index(' ') + (line_split+4):]
    # tjekker for indhold i synack og validerer IP ved hjælp af inet_aton
    if "com-0 accept" in syn_ack and socket.inet_aton(received_ip):
        ack = 'com-' + str(counter) + ' accept'
        sent_ack = sock.sendto(ack.encode(char_encoding), server_address)
        # syn-synack-ack færdiggjort og boolean sættes til true
        # så der kan sendes alm. beskeder mellem client og server
        handshake_check = True
        # tjekker config fil for indhold
        if parser.get('setting', 'KeepALive') == 'True':
            delay_time = 3
            # opretter en tråd til at køre heartbeat funktionen på med to argumenter
            t = threading.Thread(target=heartbeat, name='con-h 0x00', args=(delay_time, 'con-h 0x00'))
            t.start()
            # opretter en anden tråd til at køre shutdown check funktionen
            t2 = threading.Thread(target=check_for_shutdown)
            t2.start()

# sørger bare for at lukke socket hvis syn-synack-ack mislykkes
finally:
    if not handshake_check:
        print('closing socket')
        sock.close()

# while loop til at sende alm. beskeder frem og tilbage mellem client og server
while handshake_check:
    message_input = input()
    msg = 'msg-' + str(counter) + '=' + message_input
    sent_msg = sock.sendto(msg.encode(char_encoding), server_address)
    enc_res, server = sock.recvfrom(bufsize)
    res = enc_res.decode(char_encoding)
    # regular expression brugt for at kunne få server svar counteren
    # grupperes til 1, da vi kun vil have metacharacteren * og ikke hele stringen returneret
    pre_count = int(re.search('res-(.*)=', res).group(1))
    counter = pre_count + 1
    if counter - pre_count == 1 and 'res-' in res:
        received_message = res[res.index('=') + 1:]
        print(received_message)
