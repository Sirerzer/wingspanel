print('''
                     ____
__  WebPanel   _____/___/_______ _______ ______
\_____\    \/\/    /   /       /  __   /   ___/
   \___\          /   /   /   /  /_/  /___   /
        \___/\___/___/___/___/___    /______/
                            /_______/ 0.0.3
''')
import db
import yml
import listen






listen.run(debug=yml.debug,port=yml.port)