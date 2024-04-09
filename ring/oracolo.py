import socket
from sys import argv
import logging
import re
import json

# l'oracolo fa management della struttura ad anello

# decodifica il messaggio di join ricevuto, questa funzione viene chiamata nella funzione decodeMessage
def decodeJoin(addr, mess):
    result = re.search('(\{[a-zA-Z0-9\"\'\:\.\, ]*\})' , mess) # sempre in mess cerco un pattern json
    if bool(result):
        logging.debug('RE GROUP(1) {}'.format(result.group(1)))
        action = json.loads(result.group(1)) # trasformo la prima occorenza in dizionario python che contiene le informazioni del nodo che sta facendo il join come porta e indirizzo  
    else:
        action = {}
    
    action['command'] = 'join'

    return action

# decodifica il messaggio di leave ricevuto, questa funzione viene chiamata nella funzione decodeMessage
def decodeLeave(addr, mess):
    result = re.search('(\{[a-zA-Z0-9\"\'\:\.\, ]*\})' , mess) # sempre in mess cerco un pattern json
    if bool(result):
        logging.debug('RE GROUP(1) {}'.format(result.group(1)))
        action = json.loads(result.group(1)) # trasformo la prima occorenza in dizionario python che contiene le informazioni del nodo che sta facendo il leave come porta e indirizzo
    else:
        action = {}
    
    action['command'] = 'leave'
    
    return action

def decodeMessage(addr, mess):
    result = re.search('^\[([A-Z]*)\]' , mess) # riconosce una stringa di lettere maiuscole tra parentsi quadre 
    if bool(result):
        command = result.group(1) # ci potrebbero stare più corrispondenze, così prendo la prima
        logging.debug('COMMAND: {}'.format(command))

        '''
        if command == 'JOIN':
            decodeJoin(addr, mess)
        else if command == 'LEAVE':
            decodeLEAVE(addr, mess)
        '''

        try:
            # viene associato ad action una di queste due funzioni a seconda del comando ricevuto dalla funzione decodeMessage, 
            # oltre a effettuare l'associazione vengono passati i due parametri delle funzioni possibili
            action = {
                'JOIN'  : lambda param1,param2 : decodeJoin(param1, param2),
                'LEAVE' : lambda param1,param2 : decodeLeave(param1, param2)
            }[command](addr, mess)
        except:
            action = {}
            action['command'] = 'unknown'
    # altrimenti comando non valido 
    else: 
        action = {}
        action['command'] = 'invalid'

    logging.debug('ACTION: {}'.format(action))

    return action

# 
def updateRingJoin(action, listOfNodes):
    logging.debug('RING JOIN UPDATE')
    node = {} # inizializza un nuovo dizionario vuoto che sarà utilizzato per memorizzare le informazioni del nuovo nodo


    id_ = 1 # inizializzo l'id del nuovo nodo a 1
    idList = [int(eNode['id']) for eNode in listOfNodes] # lista di id dei nodi presenti nell'anello

    # Il ciclo for successivo cerca il primo ID non utilizzato nella lista di nodi e lo assegna al nuovo nodo.
    for i in range(1, len(listOfNodes)+2): # metto +2 (potevo mettere anche +1) perche se ho n nodi, il nuovo nodo avrà id n+1esimo
        if i not in idList:
            id_ = i
            break
    
    # riempio il dizionario node prima creato
    node['id']   = str(id_)      # id del nodo
    node['port'] = action['port'] # porta del nodo
    node['addr'] = action['addr'] # indirizzo del nodo

    # Verifica esistenza nodo nella lista di nodi
    nodes = [(eNode['addr'], eNode['port']) for eNode in listOfNodes]

    # controllo se ip e porta sono gia presenti nel ring, se non ci stanno aggiungo il nodo senno non lo aggiungo e ritorno false
    if (node['addr'], node['port']) not in nodes:
        logging.debug('OK:  Adding node {}:{}'.format(node['addr'], node['port']))
        listOfNodes.append(node) # aggiungo il nodo alla lista in coda 
    else:
        logging.debug('NOK: Adding node {}:{}'.format(node['addr'], node['port']))
        return False
    #
    return True

def updateRingLeave(action, listOfNodes):
    logging.debug('RING LEAVE UPDATE')

    # list comprension per ottenre il dizionario di nodi con chiave id e con valore il nodo stesso con tutte le sue informazioni
    dictOfNodes = {eNode['id'] : eNode for eNode in listOfNodes}
    
    # Verifica esistenza nodo che sta facendo il leave nella lista di nodi, ovviamente se non esiste esco
    if action['id'] not in dictOfNodes:
        logging.debug('NOK: Remove node {}:{}'.format(action['addr'],action['port']))
        return False
    
    # identifico il nodo da rimuovere con tutte le sue informazioni 
    nodeToRemove = dictOfNodes[action['id']]

    logging.debug('Removing node {}:{}'.format(nodeToRemove['addr'], nodeToRemove['port']))

    # controllo prima se il nodo da rimuovere ha una corrispondeza completa in termini non solo di id ma anche di porta e indirizzo IP
    if action['addr'] == nodeToRemove['addr'] and action['port'] == nodeToRemove['port']:
        logging.debug('OK:  Remove node {}:{}'.format(action['addr'],action['port']))
        listOfNodes.remove(nodeToRemove) # una volta verificato, lo posso togliere definitivamente dalla struttura 
    else:
        # altrimenti da errore
        logging.debug('NOK: Remove node {}:{}'.format(action['addr'],action['port']))
        return False
    #
    return True

def updateRing(action, listOfNodes, oracleSocket):
    logging.info('RING UPDATE: {}'.format(action)) # loggo l'azione che sto facendo e le infromazioni del nodo che lo fa  
    
    try:
        result = {
            'join'  : lambda param1,param2 : updateRingJoin(param1, param2),
            'leave' : lambda param1,param2 : updateRingLeave(param1, param2)
        }[action['command']](action, listOfNodes)
    except:
        result = False
        return result

    sendConfigurationToAll(listOfNodes, oracleSocket)
    
    return result

# serve a mandare la nuova configurazione a tutti i nodi dell'anello, serve sia quando ho un join che quando ho un leave
def sendConfigurationToAll(listOfNodes, oracleSocket):
    N = len(listOfNodes) # lista dei nodi aggiornati, ora è il momento di aggiornare anche la struttura fisica   

    for idx, node in enumerate(listOfNodes):# per ogni nodo nella lista di nodi, idx è indice e node sono tutte le informazioni
        # ORA CREO UN MESSAGGIO CHE CONTIENE UNA NUOVA CONFIGURAZIONE PER IL NODO
        if idx == N-1: # se l'indice è uguale alla lunghezza della lista di nodi -1
            nextNode = listOfNodes[0] # il prossimo nodo è il primo della lista nel caso in cui stiamo all'ultimo nodo
        else: # altrimenti il prossimo nodo è il successivo nella lista
            nextNode = listOfNodes[idx + 1]
        #logging.debug('UPDATE NODE: ({}) {}:{} --> ({}) {}:{}'.format(\
        #        node['id'],     node['addr'],     node['port'], \
        #        nextNode['id'], nextNode['addr'], nextNode['port']))
        
        # per ogni nodo sto inviando un messaggio di configurazione, dicendo in particolare qual'è il prossimo nodo
        addr, port = node['addr'], int(node['port'])
        message = {}
        message['id'] = node['id']
        message['nextNode'] = nextNode
        message = '[CONF] {}'.format(json.dumps(message)) 
        logging.debug('UPDATE MESSAGE: {}'.format(message))
        oracleSocket.sendto(message.encode(), (addr, port)) # invio il messaggio di configurazione al nodo

if __name__ == '__main__':
    
    # oracolo ha un suo indirizzo IP e porta associata, perche i nodi devono sapere dove mandare i messaggi di join e leave
    IP     = argv[1]
    PORT   = int(argv[2])
    bufferSize  = 1024
    listOfNodes = []

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    
    # creo il socket per la comunicazione con i nodi
    oracleSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    oracleSocket.bind( (IP, PORT) )

    logging.info("ORACLE UP AND RUNNING!")
    
    # ciclo infinito per ricevere i messaggi dai nodi
    while True:
        # riceve richiesta da un nodo 
        mess, addr = oracleSocket.recvfrom(bufferSize)
        dmess = mess.decode('utf-8') 

        logging.info('REQUEST FROM {}'.format(addr))
        logging.info('REQUEST: {}'.format(dmess))
        
        # decodifica richiesta trasformandola in comando da eseguire, "action"
        action = decodeMessage(addr, dmess)

        # aggiorna la configurazione dell'anello
        updateRing(action, listOfNodes, oracleSocket)

        logging.info('UPDATED LIST OF NODES {}'.format(listOfNodes))
