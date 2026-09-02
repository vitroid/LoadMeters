.PHONY: install test

PYTHON ?= $(shell command -v python2.6 2>/dev/null || command -v python2.7 2>/dev/null || command -v python 2>/dev/null || command -v python3 2>/dev/null)

install:
	@if [ -z "$(PYTHON)" ]; then echo "python not found"; exit 1; fi
	@echo "Installing to /opt/diskreporter using $(PYTHON)"
	sudo mkdir -p /opt/diskreporter/diskreporter
	sudo cp -a diskreporter/*.py /opt/diskreporter/diskreporter/
	sudo chmod -R 755 /opt/diskreporter
	test -f /etc/diskreporter.json || sudo install -m 0644 diskreporter.json.example /etc/diskreporter.json
	@if [ -d /etc/avahi/services ]; then \
		sudo install -m 0644 avahi/diskreporter.service /etc/avahi/services/; \
	else \
		echo "Avahi services dir not found; skip mDNS advertise"; \
	fi
	sudo install -m 0755 bin/diskreporter /usr/local/bin/diskreporter || sudo install -m 0755 bin/diskreporter /usr/bin/diskreporter
	@if command -v systemctl >/dev/null 2>&1 && [ -d /etc/systemd/system ]; then \
		echo "Installing systemd unit"; \
		PYTHON=$(PYTHON) WORKDIR=/opt/diskreporter; \
		sed -e "s!@PYTHON@!$$PYTHON!g" -e "s!@WORKDIR@!$$WORKDIR!g" < systemctl/diskreporter.tmpl | sudo tee /etc/systemd/system/diskreporter.service >/dev/null; \
		sudo systemctl daemon-reload; \
		sudo systemctl enable diskreporter; \
		sudo systemctl stop diskreporter || true; \
		sudo systemctl start diskreporter; \
	else \
		echo "Installing SysV init script"; \
		sudo install -m 0755 init.d/diskreporter /etc/init.d/diskreporter; \
		if command -v chkconfig >/dev/null 2>&1; then sudo chkconfig --add diskreporter; sudo chkconfig diskreporter on; fi; \
		if command -v update-rc.d >/dev/null 2>&1; then sudo update-rc.d diskreporter defaults; fi; \
		sudo /etc/init.d/diskreporter stop || true; \
		sudo /etc/init.d/diskreporter start; \
	fi
	@echo "Installation completed. curl http://localhost:8087/v1/info"

test:
	PYTHONPATH=. $(PYTHON) -m diskreporter.tests
