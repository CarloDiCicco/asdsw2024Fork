import socket
from sys import argv
import re
from threading import Thread, Lock
import json

def decodeCommand(message, stato):
    regexCOMMAND = r"^\[([A-Z]+)\]" # riconosce un comando 
    regexJSON = r"(\{[\"a-zA-Z0-9\,\ \:\"\]\[]+\})" # riconosce un json
    
    # sono le azioni che puoi fare con i comandi
    withArgs = {"SUBSCRIBE", "UNSUBSCRIBE", "SEND"}    

    command = re.findall(regexCOMMAND, message)[0] # prendo il comando, prende il primo comando che trova grazie a "[0]"
    comando = None

    # se il comando esiste allora lo gestisco
    if command:
        comando = dict()
        comando['azione'] = command
        if command in withArgs and stato == "CONNESSO":
            stringa = re.findall(regexJSON, message)[0]
            parametri = json.loads(stringa)
            comando['parametri'] = parametri 

    return comando # ritorna il comando che sarebbe un dizionario di dizionari

# funzionne che aggiorna le connessioni effettive
def updateState(id_, stato, comando):
    global activeConnections
    global mutexACs 
    
    # PRE-CONNESSIONE vuol dire che sei connesso tramite thread ma ancora non puoi mandare i comandi e farli effettuare
    if stato == "PRE-CONNESSIONE": 
        if comando['azione'] == "CONNECT":
            newStato = "CONNESSO"
            
            mutexACs.acquire()
            activeConnections[id_]['connected'] = True
            mutexACs.release()
            print('{} connected!'.format(id_))

            return newStato

    if stato == "CONNESSO":
        if comando['azione'] == "DISCONNECT":
            newStato = "IN-USCITA"
            return newStato

    return stato

def subscribe(id_, conn, comando):
    global activeConnections
    global mutexACs 
    global mutexTOPICs
    global topics

    if "topic" in comando['parametri']:

        topic = comando['parametri']['topic']
        
        # aggiorno il set dei canali specifici a cui l'utente si vuole connettere
        mutexACs.acquire()
        activeConnections[id_]["topics"].add(topic)
        mutexACs.release()

        mutexTOPICs.acquire()
        # se non c'è il topic lo aggiungo
        if not topic in topics:
            topics[topic] = set()
        # aggiungo l'id al topic
        topics[topic].add(id_)
        mutexTOPICs.release()
        print(topics)
            
        response = 'Sottoscritto al topic: {}\n'.format(topic)
        conn.sendall(response.encode()) # manda solo al client che si è sottoscritto in quel momento

# serve per unsubscribe
def unsubscribe(id_, conn, comando):
    global activeConnections
    global mutexACs 
    global mutexTOPICs
    global topics

    topic = comando['parametri']['topic']

    mutexACs.acquire()
    activeConnections[id_]["topics"].remove(topic)
    mutexACs.release()

    mutexTOPICs.acquire()
    if topic in topics:
        if id_ in topics[topic]:
            # levo id dal topic
            topics[topic].remove(id_)
        if len(topics[topic]) == 0:
            del topics[topic]
    mutexTOPICs.release()
    print(topics)
    
    response = 'Cancellazione della sottoscrizione al topic: {}\n'.format(topic)
    conn.sendall(response.encode())

def send(id_, conn, comando):
    global activeConnections
    global mutexACs 
    global mutexTOPICs
    global topics

    topic = comando["parametri"]["topic"]
    message = comando["parametri"]["message"]

    risposta = dict()
    risposta["id"] = id_
    risposta["topic"] = topic
    risposta["messaggio"] = message

    stringa = json.dumps(risposta) + '\n'
    print(stringa)

    mutexACs.acquire()
    mutexTOPICs.acquire()
    subscribers = topics[topic] # acquisisco tutti gli utenti che sono iscritti a quel topic
    # mando una copia del messaggio a tutti gli utenti
    for subID in subscribers:
        recv_conn = activeConnections[subID]["connessione"]
        recv_conn.sendall(stringa.encode())
    mutexTOPICs.release()
    mutexACs.release()

def disconnect(id_):
    global activeConnections
    global mutexACs 
    global mutexTOPICs
    global topics

    mutexACs.acquire()
    curr_topics = activeConnections[id_]["topics"]    
    mutexACs.release()

    mutexTOPICs.acquire()
    # mi scorro tutti i topic a cui è registrato e lo tolgo da tutti 
    for topic in curr_topics:
        topics[topic].remove(id_)
        # se poi il topic ha nessun iscritto cancello anche il topic
        if len(topics[topic]) == 0:
            del topics[topic]
    mutexTOPICs.release()

    mutexACs.acquire()
    del activeConnections[id_]
    mutexACs.release()
    conn.close()

# funzione che applica il comando effettivo 
def applyCommand(id_, conn, comando, stato):
    if (stato == "CONNESSO"):
        if comando['azione'] == "SUBSCRIBE":
            subscribe(id_, conn, comando) # è una funzione definita sopra
            return True
        if comando['azione'] == "UNSUBSCRIBE":
            unsubscribe(id_, conn, comando) # è una funzione definita sopra
            return True
        if comando['azione'] == "SEND":
            send(id_, conn, comando)
            return True
        if comando['azione'] == "DISCONNECT":
            disconnect(id_)
            return True
    return False

def connection_manager_thread(id_, conn):
    stato = "PRE-CONNESSIONE"               # CONNESSO, IN-USCITA (ci sono 3 possibili stati)
    print('Client: {}'.format(id_))

    while not (stato == "IN-USCITA"):
        data = conn.recv(1024)
        if not data:
            break
        # tre funzioni implementate per gestire i messaggi nel caso in cui i dati nel messaggio ci siano  
        comando = decodeCommand(data.decode('utf-8'), stato) # funzione che sta sopra all'inizio
        applyCommand(id_, conn, comando, stato) # funzione che sta subito sopra
        stato = updateState(id_, stato, comando)
    
if __name__ == '__main__':

    localIP     = argv[1]
    localPORT   = int(argv[2])
    # dizionario di dizionari che serve per garantire che le active connection non vengano modificate contemporaneamente da piu processi/thread
    global activeConnections # dizionario di dizionari
    activeConnections = {}
    global mutexACs
    # mutex che serve per garantire che i topic non vengano modificati contemporaneamente da piu processi/thread
    global mutexTOPICs
    mutexACs = Lock()
    mutexTOPICs = Lock()
    global topics 
    topics = dict() # dizionario che contiene i topic e i relativi id
    curr_id = -1

    TCPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    TCPServerSocket.bind((localIP, localPORT))
    
    try:
        # qui si accettano le connessioni e successivamente si avviano i thread di gestione 
        while True:
            print('Broker UP ({},{}), waiting for connections ...'.format(localIP, localPORT))
            TCPServerSocket.listen()                    
            conn, addr = TCPServerSocket.accept()   

            mutexACs.acquire()
            # l'elemento del dizionario contiene diverse informazioni ed ogni volta che si accetta una nuova connessione si aggiorna il dizionario  
            activeConnections[curr_id + 1] = {
                    'address': addr,
                    'connessione': conn,
                    'connected': False, # serve per capire se l'utente è connesso, viene gestita sopra
                    'id': curr_id + 1,
                    'topics': set()
                    }
            curr_id += 1
            
            mutexACs.release()
            
            Thread(target=connection_manager_thread, args=(curr_id, conn),).start()  
    finally:
        if TCPServerSocket:
            TCPServerSocket.close()
