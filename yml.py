import yaml
from datetime import *

    
current_time = datetime.now().strftime('%H:%M:%S')
print(f"[{current_time}] load the config")
try:
    with open("/etc/webpanel/config.yml", 'r') as stream:
        try:
            # Chargement du fichiers
            config = yaml.load(stream,Loader=yaml.FullLoader)
            # Récupération des personnes
            port = config["port"]
            debug = config["debug"]
            token = config["token"]
            remote = config["remote"]
            mode = config['mode']
            ssl = config['ssl']
            certfile = config['certfile']
            keyfile = config['keyfile']

            # Lecture des personnes une à une
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"[{current_time}] finish to loading the config")
        except yaml.YAMLError as ex:
            print("YAML FILE HAS SYNTAX ERROR :")
            print(ex)
            port = ''
            debug = ''
            token = ''
            remote = ''
            mode = ''
            ssl = ''
            certfile =''
            keyfile = ''
            
except FileNotFoundError:
    print('''
              -------------------------------------------------------------------------------
              Wings est a configuré via le panel allez dans nodes puis config pui auto deploy
              ou copier coller le contenue
              -------------------------------------------------------------------------------
    ''')
    port = ''
    debug = ''
    token = ''
    remote = ''
    mode = ''
    ssl = ''
    certfile =''
    keyfile = ''
def test_yml():
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
                token = config["token"]
                remote = config["remote"]
                # Lecture des personnes une à une
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"[{current_time}] finish to loading the config")
            except yaml.YAMLError as ex:
                print("YAML FILE HAS SYNTAX ERROR :")
                print(ex)
                exit()

    except FileNotFoundError:
        print('''
                  -------------------------------------------------------------------------------
                  Wings est a configuré via le panel allez dans nodes puis config pui auto deploy
                  ou copier coller le contenue
                  -------------------------------------------------------------------------------
        ''')
        port = ''
        debug = ''
        token = ''
        remote = ''
        mode = ''
        ssl = ''
        certfile =''
        keyfile = ''
