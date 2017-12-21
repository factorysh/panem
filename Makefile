W=/opt/panem
PYTHON_VERSION=$(shell python3 -V | grep  -o -e "3\.\d*")
UNAME=$(shell uname)


venv/$(UNAME)/bin/pytest: | venv/$(UNAME)/lib/python$(PYTHON_VERSION)/site-packages/flask
	./venv/$(UNAME)/bin/pip install .[test]

venv/$(UNAME)/lib/python$(PYTHON_VERSION)/site-packages/flask: | venv/$(UNAME)/bin/python
	./venv/$(UNAME)/bin/pip install .

venv/$(UNAME)/bin/python: | venv/$(UNAME)
	python3 -m venv venv/$(UNAME)
	./venv/$(UNAME)/bin/pip install --upgrade pip
	./venv/$(UNAME)/bin/pip install wheel

venv/$(UNAME):
	mkdir -p venv/$(UNAME)

dev: | venv/$(UNAME)/bin/python
	./venv/$(UNAME)/bin/pip install -e .

up:
	docker-compose up -d
	docker-compose ps

down:
	docker-compose down

clean:
	rm -rf venv bin include lib pip-selfcheck.json pyvenv.cfg

docker-venv:
	docker run --rm \
		-u `id -u` \
		-v ~/.cache/pip:/.cache/pip \
		-w $(W) \
		-v `pwd`:$(W) \
	  	python:3.5 \
   		make

test: up
	docker-compose run -T --rm web \
		./venv/Linux/bin/pytest --cov-report term-missing --cov panem -sxv tests

doc: up
	curl -o docs/swagger.json 0.0.0.0:5000/swagger.json
