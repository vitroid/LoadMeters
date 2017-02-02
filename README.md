It requires [processing.js](http://processingjs.org).

#On the server side
##Preparation
Install ruptime (unix command) on each machine.
###MacOSX
Put bsd.rwhod.plist in the system (on Terminal.app).

    sudo cp bsd.rwhod.plist /Library/LaunchDaemons/

Launch it by hand. (It will be launched automatically after reboot).

    launchctl load /Library/LaunchDaemons/bsd.rwhod.plist
###CentOS
Install.

    yum install rwho

Activate.

    chkconfig rwhod on

Launch by hand (First time only.)

    /etc/init.d/rwhod start
###debian
Install, activate, and launch.

    apt-get install rwho rwhod

##Installation
Select a machine to use as the web server.  Put processing.js in the same directory from [processing.js](http://processingjs.org).
Run the ruptime2.py micro web server on that machine.  It collects the CPU load info by ruptime command and serve it as a text file.  It accepts the HTTP request at 6502 port.

#On the client side
Open http://webserver:6502 in the web browser.  You will see the loadmeters on the web.
