all:
	@echo "Run 'make install' to install."

install:
	(umask 0022 && pip3 install .)
