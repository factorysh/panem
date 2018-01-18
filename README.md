Panem
=====

> frangensque panem & gustans

Spawn instances of one project, with _docker-compose_ and _tawa_.

Test it
-------

    make test

Read the swagger doc
--------------------

```
make up
open http://127.0.0.1:5000
```

Or use this URL https://raw.githubusercontent.com/factorysh/panem/master/docs/swagger.json
with some online editor :

* http://petstore.swagger.io/
* https://editor.swagger.io//

CLI
---

Use panem from cli:

```
$ pip install -e git+git@github.com:factorysh/panem.git#egg=panem
$ panem-cli -h

```

Licence
-------

GPL v3. Copyright ©2017 Bearstech
