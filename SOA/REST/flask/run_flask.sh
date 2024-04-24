#!/usr/bin/bash

# un file sh è un file che contiene istruzioni da eseguire in terminale linux

# Run the flask app, scrivo in  riga di comando questo file e il file python che rappresenta la risorsa a cui accedere
flask --app $1 run --port=6000 --host=0.0.0.0
./