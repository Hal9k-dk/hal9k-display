deploy:
	ansible-playbook --inventory=inventory/hosts.ini site.yml
