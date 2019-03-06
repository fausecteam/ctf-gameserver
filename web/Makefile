SOURCE_DIR ?= ctf_gameserver/web
EXT_DIR ?= $(SOURCE_DIR)/static/ext

.PHONY: dev prod ext prod-db lint
.INTERMEDIATE: bootstrap.zip

dev: $(SOURCE_DIR)/dev-db.sqlite3 ext
prod: prod-db ext
ext: $(EXT_DIR)/jquery.min.js $(EXT_DIR)/bootstrap $(SOURCE_DIR)/registration/countries.csv


$(SOURCE_DIR)/dev-db.sqlite3: $(SOURCE_DIR)/registration/countries.csv
	./dev_manage.py makemigrations templatetags registration scoring flatpages
	./dev_manage.py migrate
	./dev_manage.py createsuperuser --username admin --email ''

prod-db:
	./prod_manage.py makemigrations templatetags registration scoring flatpages
	./prod_manage.py migrate auth
	./prod_manage.py migrate
	@echo 'Run `./prod_manage.py createsuperuser` to create an initial superuser account!'

$(EXT_DIR)/jquery.min.js:
	mkdir -p $(EXT_DIR)
	curl https://code.jquery.com/jquery-1.11.3.min.js -o $@

bootstrap.zip:
	curl -L https://github.com/twbs/bootstrap/releases/download/v3.3.5/bootstrap-3.3.5-dist.zip -o $@

$(EXT_DIR)/bootstrap: bootstrap.zip
	mkdir -p $(EXT_DIR)
	unzip -n $< -d $(EXT_DIR)
	mv -v $(EXT_DIR)/bootstrap-3.3.5-dist $(EXT_DIR)/bootstrap

$(SOURCE_DIR)/registration/countries.csv:
	# Official download link from http://data.okfn.org/data/core/country-list, under Public Domain
	curl https://raw.githubusercontent.com/datasets/country-list/master/data.csv -o $@


lint:
	# Run Pylint and pep8 to check the code for potential errors and style guideline violations, but ignore
	# their exit codes
	-pylint $(SOURCE_DIR)
	-pep8 --max-line-length=109 $(SOURCE_DIR)
