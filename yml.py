import yaml
from datetime import *
def load():
    
    current_time = datetime.now().strftime('%H:%M:%S')

    print(f"[{current_time}] load the config")
    try:
        with open("config.yml", 'r') as stream:
            try:
                # Chargement du fichiers
                config = yaml.load(stream,Loader=yaml.FullLoader)

                # Récupération des personnes
                port = config["port"]
                debug = config["debug"]
                ACCESS_TOKEN = config["token"]
                remote = config["remote"]
                # Lecture des personnes une à une
                current_time = datetime.now().strftime('%H:%M:%S')

                print(f"[{current_time}] finish to loading the config")
            except yaml.YAMLError as ex:
                print("YAML FILE HAS SYNTAX ERROR :")
                print(ex)
    except FileNotFoundError:
        print('''
                  -------------------------------------------------------------------------------
                  Wings est a configuré via le panel allez dans nodes puis config pui auto deploy
                  ou copier coller le contenue
                  -------------------------------------------------------------------------------
        ''')
        port = ''
        debug = ''
        ACCESS_TOKEN = ''
        remote = ''