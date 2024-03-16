import socket
from sys import argv
import re
from threading import Thread, Lock

#questa funzione viene chiamata dal thread di gestione della connessione
def sendToAll(addr, data):
    global activeConnections
    global mutex

    # fondamentale l'uso del mutex perche se qualcuno provasse a cambiare la  struttura del  dizionario il ciclo for  andrebbe in errore
    mutex.acquire()
    # scorro tutte le coppie indirizzo e connessione connesse, e se l'indirizzo non è quello che ha chiesto il servizio mando il messaggio
    for eaddr, econn in activeConnections.items():
        if not eaddr == addr:
            econn.sendall(data)
    # dopo aver concluso di aver mandato i messaggi a  tutti gli altri allora rilascio il mutex perche il compito è concluso 
    mutex.release()

def connection_manager_thread(addr, conn):
    # sono puntatori 
    global activeConnections
    global mutex
    print('Client: {}'.format(addr))
    # non c'è l'opzione di TOGGLE 
    while True:
        data = conn.recv(1024)
        if not data:
            break
        if bool(re.search('^\[STOP\]', data.decode('utf-8'))):
            break
        print('{}: chat message: {}'.format(addr, data[:-1].decode('utf-8')))
        
        # viene chiamata la funzione di sopra
        dataToSend = '{}: {}'.format(addr, data.decode('utf-8'))

        sendToAll(addr, dataToSend.encode())

    mutex.acquire()
    # levo dalle connessioni attive perche è chiusa
    del activeConnections[addr]
    mutex.release()
    conn.close()

if __name__ == '__main__':

    localIP     = argv[1]
    localPORT   = int(argv[2])
    
    # dizionario delle connessione attive
    global activeConnections
    activeConnections = {}
    # mutex per accesso al dizionario delle connessioni attive
    global mutex
    mutex = Lock()


    TCPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    TCPServerSocket.bind((localIP, localPORT))
    
    try:

        while True:
            print('Chat Server UP ({},{}), waiting for connections ...'.format(localIP, localPORT))
            TCPServerSocket.listen()
            # conn e addr sono puntatori
            conn, addr = TCPServerSocket.accept()

            mutex.acquire()
            activeConnections[addr] = conn
            mutex.release()
            
            Thread(target=connection_manager_thread, args=(addr, conn),).start()

    finally:
        if TCPServerSocket:
            TCPServerSocket.close()
