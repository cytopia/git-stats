
help:
	@echo "build         Clone/update repositories"
	@echo "show          Show statistics"

build:
	./bin/git_stats.py -c etc/conf.yml -i

show:
	./bin/git_stats.py -c etc/conf.yml
