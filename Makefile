install:
#	install -d -m 0755 /var/www/proximity
#	install -m 0644 jquery.js *png index.html whiteback.css /var/www/proximity
	install -d -m 0755 /var/log/loadmeters
	cp loadmeters.service /lib/systemd/system/
	systemctl daemon-reload
	systemctl enable loadmeters
	systemctl restart loadmeters  
