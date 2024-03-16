import socket
from sys import argv
import re
from threading import Thread, Lock

# questa è la funzione che rappresenta il thread di gestione della richiesta
def connection_manager_thread(addr, conn):
    print('Client: {}'.format(addr))
    toggle = True # variabile toggle è locale per ogni thread di gestione e quindi per ogni client connesso
    while True:
        data = conn.recv(1024)
        if not data:
            break
        if bool(re.search('^\[STOP\]', data.decode('utf-8'))):
            break
        if bool(re.search('^\[TOGGLE\]', data.decode('utf-8'))):
            toggle = not toggle
        print('{}: echo message: {}'.format(addr, data[:-1].decode('utf-8')))
        if toggle:
            conn.sendall(data)
    conn.close()


if __name__ == '__main__':

    localIP     = argv[1]
    localPORT   = int(argv[2])

    TCPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    TCPServerSocket.bind((localIP, localPORT))

    # ogni volta che arriva una richiesta c'è un processo principale che avvia un thread che si occupa di gestire la richiesta, ogni richiesta equivale ad un thread avviato
    while True:
        print('TCP Server UP ({},{}), waiting for connections ...'.format(localIP, localPORT))
        TCPServerSocket.listen()
        conn, addr = TCPServerSocket.accept()
        # creo il thread che deve gestire la connessione e lo avvio 
        Thread(target=connection_manager_thread, args=(addr, conn),).start()
    
    TCPServerSocket.close()

