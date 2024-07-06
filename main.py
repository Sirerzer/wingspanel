print('''
                     ____
__  WebPanel   _____/___/_______ _______ ______
\\_____\\    \\/\\/    /   /       /  __   /   ___/
   \\___\\          /   /   /   /  /_/  /___   /
        \\___/\\___/___/___/___/___    /______/
                            /_______/ 0.0.6
''')

import db
import yml
import listen



if(yml.port == ''):
   print("Programe finish")
else:
   listen.run(debug=yml.debug,port=yml.port)