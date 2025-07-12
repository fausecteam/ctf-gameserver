SOURCE_DIR ?= src
WEB_DIR ?= $(SOURCE_DIR)/ctf_gameserver/web
EXT_DIR ?= $(WEB_DIR)/static/ext
DEV_MANAGE ?= src/dev_manage.py
TESTS_DIR ?= tests

.PHONY: dev build ext migrations run_web test lint run_docs clean
.INTERMEDIATE: bootstrap.zip

dev: $(WEB_DIR)/dev-db.sqlite3 ext
build: ext migrations
ext: $(EXT_DIR)/jquery.min.js $(EXT_DIR)/bootstrap $(WEB_DIR)/registration/countries.csv


migrations: $(WEB_DIR)/registration/countries.csv
	$(DEV_MANAGE) makemigrations --no-input templatetags registration scoring flatpages vpnstatus

$(WEB_DIR)/dev-db.sqlite3: migrations $(WEB_DIR)/registration/countries.csv
	$(DEV_MANAGE) migrate
	DJANGO_SUPERUSER_PASSWORD=password $(DEV_MANAGE) createsuperuser --no-input --username admin --email 'admin@example.org'

$(EXT_DIR)/jquery.min.js:
	mkdir -p $(EXT_DIR)
	curl https://code.jquery.com/jquery-1.11.3.min.js -o $@

bootstrap.zip:
	curl -L https://github.com/twbs/bootstrap/releases/download/v3.3.5/bootstrap-3.3.5-dist.zip -o $@

$(EXT_DIR)/bootstrap: bootstrap.zip
	mkdir -p $(EXT_DIR)
	unzip -n $< -d $(EXT_DIR)
	mv -v $(EXT_DIR)/bootstrap-3.3.5-dist $(EXT_DIR)/bootstrap

$(WEB_DIR)/registration/countries.csv:
	# Official download link from http://data.okfn.org/data/core/country-list, under Public Domain
	curl https://raw.githubusercontent.com/datasets/country-list/master/data.csv -o $@


run_web:
	$(DEV_MANAGE) runserver

test:
	pytest --cov $(SOURCE_DIR) $(TESTS_DIR)

lint:
	# Run Pylint, pycodestyle and Bandit to check the code for potential errors, style guideline violations
	# and security issues
	pylint --rcfile $(SOURCE_DIR)/pylintrc $(SOURCE_DIR) $(TESTS_DIR)
	pycodestyle $(SOURCE_DIR) $(TESTS_DIR)
	bandit --ini bandit.ini -r $(SOURCE_DIR)

run_docs:
	mkdocs serve

docs_site: mkdocs.yml $(wildcard docs/* docs/*/*)
	mkdocs build --strict


clean:
	rm -rf src/ctf_gameserver/web/*/migrations
	rm -f src/ctf_gameserver/web/dev-db.sqlite3 src/ctf_gameserver/web/registration/countries.csv
	rm -rf src/ctf_gameserver/web/static/ext
	rm -rf build dist src/ctf_gameserver.egg-info
	rm -rf docs_site
