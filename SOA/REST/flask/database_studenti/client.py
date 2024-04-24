import requests
import json

# NELLA PAGINA WEB SI DOVEBBE VISUALIZZARE LA RISPOSTA A TUTTE LE RICHIESTE CHE VENGONO EFFETTUATE  DA QUESTO SCRIPT CHE SAREBBE IL CLIENT

#  definisco base di risorse a cui posso accedere
address = 'http://127.0.0.1:6000'

response = requests.get(address + '/api/v1/resources/students/all')
# response è un oggetto particolare che contiene molte informazioni
print('-'*80)
print('RESPONSE')
print(response)
print('-'*80)
print('RESPONSE.CONTENT')
print(response.content)
print('-'*80)
print('RESPONSE.TEXT')
print(response.text)
print('-'*80)
print('RESPONSE.JSON()')
print(response.json())


# prepara una richiesta HTTP GET con un parametro id=3
query = {'id': 3}
response = requests.get(address + '/api/v1/resources/students', params=query)
print('-'*80)
print(json.dumps(response.json(), indent=4, sort_keys=True))

newData = {
    'id': 2,
    'nome': 'Carlo',
    'cognome': 'Neri',
    'immatricolazione': 2015,
    'esami_sostenuti': 24
}

# prepara una richiesta HTTP POST con i dati di un nuovo studente da inserire
response = requests.post(address + '/api/v1/resources/students', params=newData)
print('-'*80)
print(json.dumps(response.json(), indent=4, sort_keys=True))

# prepara una richiesta HTTP GET per ottenere l'elenco completo degli studenti
response = requests.get(address + '/api/v1/resources/students/all')
print('-'*80)
print(json.dumps(response.json(), indent=4, sort_keys=True))
