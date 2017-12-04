W=/opt/panem

all: venv dev test

clean:
	rm -Rf venv

venv:
	docker run --rm -u `id -u` -v ~/.cache/pip:/.cache/pip -w $(W) -v `pwd`:$(W) \
	  	bearstech/python-dev:3 \
   		python3 -m venv venv


install:
	virtualenv -p python3 venv || python3 -m venv venv
	venv/bin/pip install -r requirements.txt

dev: venv
	docker run --rm -u `id -u` -v ~/.cache/pip:/.cache/pip -w $(W) -v `pwd`:$(W) \
	  	bearstech/python-dev:3 \
		venv/bin/pip install -e .[test]

test:
	docker run --rm -u `id -u` -v ~/.cache/pip:/.cache/pip -w $(W) -v `pwd`:$(W) \
	  	bearstech/python-dev:3 \
		venv/bin/pytest --cov-report term-missing --cov panem -sxv tests

run:
	docker run -it --rm -u `id -u` -v ~/.cache/pip:/.cache/pip -w $(W) -v `pwd`:$(W) \
		-p 5000:5000 \
		-e FLASK_APP=panem.app \
		bearstech/python-dev:3 venv/bin/python -m flask run -h 0.0.0.0 -p 5000
