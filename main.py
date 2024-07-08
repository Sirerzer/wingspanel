print('''
                     ____
__  WebPanel   _____/___/_______ _______ ______
\\_____\\    \\/\\/    /   /       /  __   /   ___/
   \\___\\          /   /   /   /  /_/  /___   /
        \\___/\\___/___/___/___/___    /______/
                            /_______/ 0.0.8
''')
import os
try:
   import argparse
   import db
   import yml
   import listen
   import os
except:
   os.system("pip install docker pyyaml pytest pytest-cov flask flask-cors")

if(yml.port == ''):
   print("Programe finish")
else:
   listen.run(debug=yml.debug,port=yml.port)