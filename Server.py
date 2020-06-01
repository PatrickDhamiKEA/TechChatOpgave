import socket
import threading
import re
from configparser import ConfigParser

server_ip = socket.gethostbyname(socket.gethostname())

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (server_ip, 5500)
sock.bind(server_address)

sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address2 = (server_ip, 5501)
sock2.bind(server_address2)
sock2.settimeout(4)

shutdown_switch = False
spam_count = 0
parser = ConfigParser()
parser.read('opt.conf')
no_spam_detected = True
check_count = -2
char_encoding = "utf-8"
bufsize = 1024


# kører på tråd 1 t og modtager et heartbeat i sekund interval defineret i clienten
# dog kan det specificeres hvor lang tid der max må gå imellem hvert heartbeat i settimeout på line 15
def check_heartbeat():
    while True:
        try:
            enc_hb_data, address = sock2.recvfrom(bufsize)
            hb_data = enc_hb_data.decode(char_encoding)
            print(hb_data)
        # hvis settimeout ikke bliver overholdt, sendes der en besked (con-res 0xFE) til clienten
        except socket.timeout:
            print('shutdown')
            # en try block i tilfælde af at clienten lukkes af andre årsager end en timeout
            try:
                res = sock2.sendto('con-res 0xFE'.encode(char_encoding), address)
                enc_hb_data, address = sock2.recvfrom(bufsize)
                hb_data = enc_hb_data.decode(char_encoding)
                # tjekker om der bliver returneret en korrekt shutdown besked fra clienten
                if hb_data.startswith('con-res 0xFF'):
                    handshake()
                else:
                    handshake()

            except:
                handshake()


# syn-synack-ack funktionen som er det første der kaldes når serveren tændes
def handshake():
    # modtager syn fra clienten
    enc_syn, address = sock.recvfrom(bufsize)
    syn = enc_syn.decode(char_encoding)
    line_split = syn.find('0')
    # finder clientens IP fra syn
    received_ip = syn[syn.index(' ') + line_split + 1:]
    # tjekker for indhold i syn og validerer IP ved hjælp af inet_aton
    if syn.startswith("com-0") and socket.inet_aton(received_ip):
        syn_ack = 'com-0 accept ' + server_ip
        # sender synack til clienten
        sent_syn_ack = sock.sendto(syn_ack.encode(char_encoding), address)
        # modtager ack fra clienten
        ack, address2 = sock.recvfrom(bufsize)
        # tjekker for indhold i ack og starter 2 tråde op, en til heartbeat og en til at tjekke for spam
        # samt kalder to metoder reset_spam og check_first_message
        if ack.decode(char_encoding).startswith("com-0 accept"):
            t = threading.Thread(target=check_heartbeat)
            t.start()
            t2 = threading.Thread(target=check_for_spam)
            t2.start()
            reset_spam()
            check_first_message()


# tjekker om første besked fra clienten starter med msg-0 og kalder så send_message med msg-0 som parameter
# og receive_message funktionerne
def check_first_message():
    enc_msg, address = sock.recvfrom(bufsize)
    msg = enc_msg.decode(char_encoding)
    if msg.startswith('msg-0'):
        send_message(msg, address)
        receive_message()
        global spam_count
        spam_count += 1


# kører på tråd 2 t2 og tjekker om spam_count er højere end max spam angivet i config fil
def check_for_spam():
    while True:
        global spam_count
        if spam_count > int(parser.get('setting', 'max_amount_of_packages')):
            global no_spam_detected
            no_spam_detected = False


# funktion til at resete spam tælleren
def reset_spam():
    # startes en tråd der med interval af 1 sekund kalder reset_spam funktionen
    threading.Timer(1.0, reset_spam).start()
    global spam_count
    spam_count = 0
    global no_spam_detected
    no_spam_detected = True


# funktion til at sende beskeder til clienten
def send_message(insert_decoded_msg, insert_address):
    global check_count
    # regular expression brugt for at kunne få client svar counteren
    # grupperes til 1, da vi kun vil have metacharacteren * og ikke hele stringen returneret
    pre_count = int(re.search('msg-(.*)=', insert_decoded_msg).group(1))
    counter = pre_count + 1
    if pre_count + check_count == -2 and insert_decoded_msg.startswith('msg-'):
        respond_for_message = 'res-' + str(counter) + '=I am server'
        res = sock.sendto(respond_for_message.encode(char_encoding), insert_address)
        global spam_count
        spam_count += 1
        check_count -= 2


# funktion til at modtage beskeder fra clienten
def receive_message():
    while no_spam_detected:
        enc_msg, address = sock.recvfrom(bufsize)
        msg = enc_msg.decode(char_encoding)
        print(msg)
        send_message(msg, address)


handshake()
