#/usr/bin/env python2.7
import cherrypy
import os.path
import os
import re
import time


#rwho name and specs
alias = {"Swindler0":"swindler0",
         "Swindler1":"swindler1",
         "Swindler3":"swindler3",
         "Swindler4":"swindler4",
         "e2":       "eris2",
         "el3":      "elara3",
         "h1"       :"helene1",       
         "h2"       :"helene2",       
         "h4"       :"helene4",       
         "o2"       :"oberon2",       
         "o3"       :"oberon3",       
         "o4"       :"oberon4",
         "r7"       :"rhea7",
         "th1"      :"thebe1",}
# processing power relative to bluebird.
# simplemd 1000 < Test/w512
X = 8
spec = {"swindler"  :["centos",64, X/11.], #11sec
        "yellowbird":["centos",4 , X/2/2.4], #??
        "stella"    :["centos",8 , X/4.05  ], #4.05sec
        "chuck"     :["centos",16, X/3.808],#3.808sec
        "bluebird"  :["centos",16, X/5.00], #5sec
        "redbird"   :["centos",24, X/5.154], #5.154sec
        "blackbird" :["centos",32, X/3.674], #3.674
        "blackbirdA" :["centos",32, X/3.674], #3.674
        "blackbirdB" :["centos7",44, X/3.674], #??
        "erdos"     :["centos",16, X/2/2.4],
        #"io"        :["lion",12],
        #"phobos"    :["snowleopard",8],
        #"eris"      :["snowleopard",8],
        #"elara"     :["snowleopard",12],
        #"lemon"     :["snowleopard",8],
        #"luffa"     :["snowleopard",8],
        #"oberon"    :["leopard",8],
        #"helene"    :["leopard",8],
        #"thebe"     :["leopard",8],
        #"rhea"      :["tiger",8],
        #"ariel"     :["tiger",4],
        #"titan"     :["tiger",4],
}

def mycmp(x,y):
    r = cmp(x[1],y[1]) #os
    if r == 0:
        r = cmp(y[2],x[2]) #core
    if r == 0:
        r = cmp(x[0],y[0]) #name
    return r

def mykey(x):
    return x[1], -x[2], x[0]
ascii = re.compile("([a-z]+)([0-9]+)")
# ascii = re.compile("[a-z]+")

class Ruptime(object):
    def index(self):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        pipe = os.popen("ruptime -a","r")
        output = []
        while True:
            line = pipe.readline()
            if len(line) == 0:
                break
            columns = line.split()
            if len(columns) == 9:
                server = columns[0]
                load = columns[-3]
                load = load[0:len(load)-1]
                load = float(load)
                if server in alias:
                    server = alias[server]
                m = re.match(ascii, server)
                if m:
                    # serverclass = m.group(0)
                    serverclass = m.group(1)
                    serverorder = m.group(2)
                    if serverclass == "blackbird":
                        if serverorder in ("1","2"):
                            serverclass = "blackbirdA"
                        else:
                            serverclass = "blackbirdB"
                    if serverclass in spec:
                        d = [server,] + spec[serverclass][0:2]
                        d += [load,]
                        if len(spec[serverclass]) == 3:
                            rel = spec[serverclass][2]
                        else:
                            rel = 1.0
                        d += [rel]
                        output.append(d)
        #output the content of the queue
        result = ""
        for data in sorted(output,key=mykey):
            for datum in data:
                result += ("%s\t" % datum)
            result += "\n"
        return result
    index.exposed = True


class Du(object):
    def Output(self,output,path):
        result = ""
        for subdir,siz in output[path]:
            result +=  ("%s\t%f\n" % (subdir,siz))
            if subdir in output:
                result += self.Output(output,subdir)
            result += "\n"
        return result

    def index(self):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        pipe = os.popen("df","r")
        output = dict()
        grandtotal = 0
        output["/"] = []
        while True:
            line = pipe.readline()
            if len(line) == 0:
                break
            columns = line.split()
            fs = columns[5]
            if fs[0] == '/':
                fs = fs[1:len(fs)]
            if fs in ("net/jukebox4/u2","net/jukebox4/r1l","net/jukebox0/r2","net/jukebox1/r3","net/jukebox2/r4","net/jukebox4/r5"):
                total = float(columns[1])
                used  = float(columns[2])
                grandtotal += total
                output["/"].append((fs,total))
                output[fs]=[]
                output[fs].append(("unused",total-used))
                output[fs].append(("used",used))
        #output the content of the queue
        result = "{0}\t{1}\n".format("/",grandtotal)
        result += self.Output(output,"/")
        result += "\n\n\n"
        return result
    index.exposed = True



class Df(object):
    def index(self):
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        pipe = os.popen("df","r")
        result = ""
        while True:
            line = pipe.readline()
            if len(line) == 0:
                break
            columns = line.split()
            fs = columns[5]
            if fs[0] == '/':
                fs = fs[1:len(fs)]
            if fs in ("misc/r0","r1s","r1l","r2","misc/r3"):
                total = float(columns[1])
                used  = float(columns[2])
                result += "{0}\t{1}\t{2}\n".format(fs,used,total)
        #output the content of the queue
        return result
    index.exposed = True



class Root(object):
    #dynamic contents are redirected here.
    du = Du()            #/du handler
    df = Df()            #/df handler
    ruptime = Ruptime()  #/ruptime handler
    def index(self):
        return open(current_dir + "/v.html", 'r').read()
    index.exposed = True




if __name__ == '__main__':
    cherrypy.server.socket_port = 6502
    cherrypy.server.socket_host = "0.0.0.0"

    cherrypy.config.update({'environment': 'embedded',
                            'log.access_file' : "/var/log/loadmeters/access.log",
                            'log.error_file' : "/var/log/loadmeters/error.log",
                            'log.screen' : False,
                            'tools.sessions.on': True,
    })
    
    
    current_dir = os.path.dirname(os.path.abspath(__file__))

    conf = {
            '/favicon.gif': { 'tools.staticfile.on': True,
                              'tools.staticfile.filename': current_dir + "/favicon.gif"},
            '/processing-1.4.1.js': { 'tools.staticfile.on': True,
                                      'tools.staticfile.filename': current_dir + "/processing-1.4.1.min.js",
                                      'tools.staticdir.content_types': {'js': 'text/javascript'}},
            '/d': { 'tools.staticfile.on': True,
                    'tools.staticfile.filename': current_dir + "/d.html"},
            '/v.html': { 'tools.staticfile.on': True,
                    'tools.staticfile.filename': current_dir + "/v.html"},
            '/v.pde': { 'tools.staticfile.on': True,
                    'tools.staticfile.filename': current_dir + "/v.pde"},
            '/v2.pde': { 'tools.staticfile.on': True,
                    'tools.staticfile.filename': current_dir + "/v2.pde"},
            '/v2.html': { 'tools.staticfile.on': True,
                    'tools.staticfile.filename': current_dir + "/v2.html"},
            }


    cherrypy.quickstart(Root(), "/", config=conf)

