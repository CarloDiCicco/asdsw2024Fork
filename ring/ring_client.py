from cmd import Cmd
from threading import Thread
from sys import argv
import time 
import os
import re
import socket
import logging
import json

# Questo script va avviato per inserire un nuovo nodo nella rete ring, passando come argomenti
# l'indirizzo IP e la porta dell'oracolo, l'indirizzo IP e la porta del nodo che si vuole inserire

# funzioen che genera il mio messaggio  elo passa all'anello 
def sendDataToRing(clientSocket, nextNode, idSorgente, idDestinazione, mess):
    # PROTOTIPO MESSAGGIO: [DATA] JSON MESSAGGIO
    messaggio = {}
    messaggio['idSorgente'] = idSorgente
    messaggio['idDestinazione'] = idDestinazione
    messaggio['payload'] = mess

    stringaMessaggio = '[DATA] {}'.format(json.dumps(messaggio))
    logging.debug('Invio Messaggio: {}'.format(stringaMessaggio))

    # INVIO MESSAGGIO
    nextNodeAddress = nextNode['addr']
    nextNodePort    = int(nextNode['port'])
    clientSocket.sendto(stringaMessaggio.encode(), (nextNodeAddress, nextNodePort))

# eredita la classe cmd, per l'uso dei promt 
class RingPrompt(Cmd):
    prompt = ''
    intro  = 'Benvenuto nel ring. Usa ? per accedere all\'help'

    def conf(self, socket, nextNode, idSorgente):
        self.socket = socket
        self.nextNode = nextNode
        self.idSorgente = idSorgente

        self.prompt = '[{}-->{}]>'.format(idSorgente, nextNode['id'])

    def do_exit(self, inp): # se l'utente scrive exit esce dal prompt, va implementato? 
        print('Ciao, alla prossima!')
        return True

    def do_send(self, inp):
        #Prototipo messaggio: send [id] <MESSAGGIO>
        result = re.search('^\[([0-9]*)\]', inp) # cerca id del destinatario
        if bool(result):
            idDestinazione = result.group(1) # prende la prima occorrenza
        result = re.search('<([a-zA-Z0-9\,\.\;\'\"\!\?<> ]*)>', inp) # cerca il messaggio
        if bool(result):
            mess = result.group(1)
        logging.debug('INVIO MESSAGGIO:\nDestinatario: {}\nMessaggio: {}'.format(idDestinazione, mess))
        
        sendDataToRing(self.socket, self.nextNode, self.idSorgente, idDestinazione, mess)

    def echo_message(self, inp):
        print('Messaggio Ricevuto: {}'.format(inp))

    #def do_help(self, inp):
    #    print("Help non ancora implementato")

    def do_shell(self, inp): # se l'utente scrive shell esegue il comando shell
        print(os.popen(inp).read())

def managePrompt(prompt):
    prompt.cmdloop()

def join(clientSocket, currNode, nextNode, oracleIP, oraclePORT):
    mess = '[JOIN] {}'.format(json.dumps(currNode)) # creo il messaggio di join
    logging.debug('JOIN MESSAGE: {}'.format(mess)) # stampo il messaggio di join
    clientSocket.sendto(mess.encode(), (oracleIP, oraclePORT)) # invio il messaggio di join all'oracolo
    mess = clientSocket.recvfrom(1024) # mi blocco in attesa di una risposta che contiene la configurazione nuova del ring che il nodo deve seguire, il messaggio è un dizionario 
    mess = mess.decode('utf-8') # decodifico il messaggio 
    logging.debug('RESPONSE: {}'.format(mess))
	
    result = re.search('(\{[a-zA-Z0-9\"\'\:\.\,\{\} ]*\})', mess) # cerca le rispondenza in json 
    if bool(result):
        logging.debug('RE GROUP(1) {}'.format(result.group(1)))	
        action = json.loads(result.group(1)) # prende la prima occorenza di result 
        currNode['id'] = action['id']
        nextNode['id'] = action['nextNode']['id']
        nextNode['addr'] = action['nextNode']['addr']
        nextNode['port'] = action['nextNode']['port']
        logging.debug('NEW CONF: \n\t currNode: {} \n\t nextNode: {}'.format(currNode, nextNode))
    else:
        action = {}

def leave(clientSocket, currNode, oracleIP, oraclePort):
    mess = '[LEAVE] {}'.format(json.dumps(currNode))
    logging.debug('LEAVE MESSAGE: {}'.format(mess))
    clientSocket.sendto(mess.encode(), (oracleIP, oraclePORT))

def sendMessage(clientSocket, nextNode, message):
    pass

# l'oracolo manda il messaggio di update di configuration al nodo con le informazioni in json
def updateConfiguration(clientSocket, currNode, nextNode, mess, prompt):
    logging.debug('UPDATE CONFIGURATION')

    result = re.search('(\{[a-zA-Z0-9\"\'\:\.\,\{\} ]*\})', mess) # cerco il json nel messaggio
    if bool(result):
        configuration = json.loads(result.group(1)) # trasformo il json in dizionario python
        logging.debug('NEW CONFIGURATION: {}'.format(configuration))
        # prendo tutte le informazioni dal dizionario
        currNode['id'] = configuration['id']
        nextNode['id'] = configuration['nextNode']['id']
        nextNode['addr'] = configuration['nextNode']['addr']
        nextNode['port'] = configuration['nextNode']['port']
        prompt.conf(clientSocket, nextNode, currNode['id']) # aggiorno la configurazione del prompt con le nuove informazioni

# se mi arriva un messaggio dati viene chiamata questa funzione    
def decodeData(clientSocket, currNode, nextNode, mess, prompt):
    logging.debug('DATA MESSAGE')
    result = re.search('(\{[a-zA-Z0-9\"\'\:\.\,\{\} ]*\})', mess) # cerco il json nel messaggio
    if bool(result):
        message = json.loads(result.group(1)) # trasformo la prima occorrenza il json in dizionario python
        logging.debug('NEW MESSAGE: {}'.format(message))
        # prendo tutte le informazioni dal dizionario
        idSorgente = message['idSorgente'] 
        idDestinazione = message['idDestinazione']
        payload = message['payload']
        if idDestinazione == currNode['id']: # allora sono io il destinatario e stampo il messsaggio
            prompt.echo_message('{}->{}: {}'.format(idSorgente, idDestinazione, payload))
        elif idSorgente == currNode['id']: # allora sono io il mittente e non faccio nulla
            logging.debug('DROPPING MESSAGE') 
        else: # altrimenti devo inoltrare il messaggio al nodo successivo 
            addr = nextNode['addr']
            port = int(nextNode['port'])
            clientSocket.sendto(mess.encode(), (addr, port))


def receiveMessage(clientSocket, currNode, nextNode, prompt):
    mess, addr = clientSocket.recvfrom(1024) # si blocca in attesa del messaggio
    mess = mess.decode('utf-8')
    logging.debug('MESSAGE FROM {}:{} = {}'.format(addr[0], addr[1], mess))

    action = False

    result = re.search('^\[([A-Z]*)\]', mess) # cerco il comando nel messaggio come [CONF] o [DATA]
    if bool(result):
        command = result.group(1) # prendo la prima occorrenza 
        if command in {'CONF', 'DATA'}: # il messaggioi pure essere di configurazione o di dati e aseconda di questo chiamo una funzione diversa 
            action = {
                'CONF' : lambda param1, param2, param3, param4, param5 : updateConfiguration(param1, param2, param3, param4, param5),
                'DATA' : lambda param1, param2, param3, param4, param5 : decodeData(param1, param2, param3, param4, param5)
            }[command](clientSocket, currNode, nextNode, mess, prompt)

    return action

if __name__ == '__main__':

    oracleIP     = argv[1]
    oraclePORT   = int(argv[2])
    clientIP     = argv[3]
    clientPORT   = int(argv[4])
    
    # Configurazione del logger, 
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.ERROR)
    
    # creo un nuovo socket UDP
    clientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    clientSocket.bind( (clientIP, clientPORT) )

    logging.info('CLIENT UP AND RUNNING')
    
    # dizionari che tengono traccia dei nodi il corrente e il successivo
    currNode = {}
    nextNode = {}

    currNode['addr'] = clientIP
    currNode['port'] = str(clientPORT)
    
    # adesione del nuovo nodo alla rete ring
    join(clientSocket, currNode, nextNode, oracleIP, oraclePORT)
    logging.debug('NEW CONFIGURATION:\n\t{}\n\t{}'.format(currNode, nextNode))
    
    # Creazione della classe prompt è una shell interattiva in cui l'utente può inviare e ricevere messaggi dal ring
    prompt = RingPrompt()
    prompt.conf(clientSocket, nextNode, currNode['id'])
    
    # Avvio un nuovo thread che esegue la funzione managePrompt con prompt come argomento.
    Thread(target=managePrompt, args=(prompt,)).start()

    # Gestione comunicazione Ring - Oracle, Ring - Ring
    while True:
        receiveMessage(clientSocket, currNode, nextNode, prompt)
