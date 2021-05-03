#!/usr/bin/env python3.8
import socket 
import re
import sys

INPUT_ERROR = "exit: input arguments error.\nUsage: python ./fileget.py -n NAMESERVER -f surl_string."
NAMESERVER_ERROR = "exit: name server error.\nServer not responding."
RESP_NAMESERVER_ERROR = "exit: name server error.\nFile server does not exist/Bad request."
FILESERVER_ERROR = "exit: file server error.\nFile server not responding."
RESP_FILESERVER_ERROR = "exit: file server error.\nFile not found/Bad request."


# Check if input is valid
if len(sys.argv) != 5:
    sys.exit(INPUT_ERROR)

if sys.argv[1] == '-n' and sys.argv[3] == '-f':
    nameserver = sys.argv[2].split(':')
    surl_string = sys.argv[4]
elif sys.argv[1] == '-f' and sys.argv[3] == '-n':
    nameserver = sys.argv[4].split(':')
    surl_string = sys.argv[2]
else:
    sys.exit(INPUT_ERROR)

if len(nameserver) != 2:
    sys.exit(INPUT_ERROR)

ip_addr = nameserver[0]
port_num = nameserver[1]

try: 
    # Check if IP address is valid
    socket.inet_aton(ip_addr)
except socket.error:
    sys.exit(INPUT_ERROR)

if port_num.isdigit():
    # Check if port number is valid
    if not 0 <= int(port_num) <= 65535:
        sys.exit(INPUT_ERROR)        
else:
    sys.exit(INPUT_ERROR)

def get_server_path(surl_string):
    """ Extract filepath from SURL string
    
    """
    if re.match(r'^fsp://(\w|-|\.)+/.+$', surl_string) == None:
        sys.exit(INPUT_ERROR)

    surl_string = surl_string[6:]
    backslash_index = 0
    for c in surl_string:
        if c == '/':
            break
        backslash_index += 1

    return surl_string[:backslash_index], surl_string[backslash_index+1:]

def nsp_send_req(nsp_adrr, file_server_name):
    """ Create client UDP socket.
    Send request to server and wait for answer.
    Get file server IP and port number.
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(10)
    mess = 'WHEREIS ' + file_server_name + ' \r\n'
    try:
        client.sendto(mess.encode(), nsp_adrr)
        mess_recv = client.recv(1024)
    except socket.error:
        return -1

    client.close()
    return mess_recv.decode()

file_server_name, path_to_file = get_server_path(surl_string)

nsp_resp = nsp_send_req((ip_addr, int(port_num)), file_server_name)

if nsp_resp == -1:
    sys.exit(NAMESERVER_ERROR)
elif re.search(r'^(ERR Syntax)|(ERR Not Found)$', nsp_resp):
    sys.exit(RESP_NAMESERVER_ERROR)
else:
    file_server_addr = nsp_resp[3:]
    file_server_addr = file_server_addr.split(':')


def create_file(path_to_file, data):
    """ Extract file name from filepath.
    Create file and write down data.
    """
    index = path_to_file.rfind('/')
    filename = path_to_file[index+1:]

    f = open(filename, 'wb')
    f.write(data)
    f.close()

def fsp_get(file_server_name, file_server_addr, path_to_file, client):
    """ Send GET request for a given client and given SURL.
    Recieve all the packets and return file data.
    """ 
    mess = 'GET ' + path_to_file + ' FSP/1.0\r\nHostname: ' + file_server_name +  '\r\nAgent: xpopos00\r\n\r\n'
    client.sendto(mess.encode(), file_server_addr)

    data = bytearray()
    while True:
        packet = client.recv(32)
        if not packet:
            break
        data.extend(packet)

    if re.search(rb'^FSP/1.0 Success', data):
        i = 0
        cnt = 0
        while cnt < 3:
            if data[i] == 10:
                cnt += 1
            i += 1

        return data[i:]
    else:
        return -1

def fsp_send_req(file_server_name, file_server_addr, path_to_file):
    """ Send request via TCP and accept incoming packets.
    Call create_file() on data.
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(file_server_addr)
    except socket.error:
        sys.exit(FILESERVER_ERROR)
        
    
    if path_to_file == '*':
        # First get index file, and then send request for each file on the given server
        files = fsp_get(file_server_name, file_server_addr, 'index', client).decode()

        for f in files.splitlines():
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
               client.connect(file_server_addr)
            except socket.error:
                sys.exit(FILESERVER_ERROR)

            fsp_resp = fsp_get(file_server_name, file_server_addr, f, client)
            if fsp_resp != -1:
                create_file(f, fsp_resp)
            else:
                sys.exit(RESP_FILESERVER_ERROR)
            
    else:
        fsp_resp = fsp_get(file_server_name, file_server_addr, path_to_file, client)
        if fsp_resp != -1:
            create_file(path_to_file, fsp_resp)
        else:
            sys.exit(RESP_FILESERVER_ERROR)


fsp_send_req(file_server_name, (file_server_addr[0], int(file_server_addr[1])), path_to_file)

