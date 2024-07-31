print('''
                     ____
__  WebPanel   _____/___/_______ _______ ______
\\_____\\    \\/\\/    /   /       /  __   /   ___/
   \\___\\          /   /   /   /  /_/  /___   /
        \\___/\\___/___/___/___/___    /______/
                            /_______/ 0.0.9
''')
import os
try:
   import argparse
   import db
   import yml
   import listen
   import os
   import proxy
   import env_check
except:
   os.system("pip install docker pyyaml pytest pytest-cov flask flask-cors")

if(yml.port == ''):
   print("Programe finish")
if yml.mode == 2 or yml.mode == 3:
   print("") 
else:

   if env_check.check_port_in_use(yml.port):
      if yml.ssl:
         listen.run(debug=yml.debug,port=yml.port,keyfile=yml.keyfile,certfile=yml.certfile)
      else:
         listen.run(debug=yml.debug,port=yml.port)
   else:
      time = db.print_current_time()
      print(f"[{time}] Fail to Starting Webpanel wings on port {yml.port} because it is already in use")