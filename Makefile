SOURCE_DIR ?= src
WEB_DIR ?= $(SOURCE_DIR)/ctf_gameserver/web
EXT_DIR ?= $(WEB_DIR)/static/ext
DEV_MANAGE ?= ../scripts/web/dev_manage.py
TESTS_DIR ?= tests

.PHONY: dev ext test lint
.INTERMEDIATE: bootstrap.zip

dev: $(WEB_DIR)/dev-db.sqlite3 ext
ext: $(EXT_DIR)/jquery.min.js $(EXT_DIR)/bootstrap $(WEB_DIR)/registration/countries.csv


$(WEB_DIR)/dev-db.sqlite3: $(WEB_DIR)/registration/countries.csv
	$(DEV_MANAGE) makemigrations templatetags registration scoring flatpages
	$(DEV_MANAGE) migrate
	$(DEV_MANAGE) createsuperuser --username admin --email ''

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


test:
	pytest --cov $(SOURCE_DIR) $(TESTS_DIR)

lint:
	# Run Pylint and pycodestyle to check the code for potential errors and style guideline violations, but
	# ignore their exit codes
	-pylint --rcfile $(SOURCE_DIR)/pylintrc $(SOURCE_DIR) $(TESTS_DIR)/test_*.py
	-pycodestyle $(SOURCE_DIR) $(TESTS_DIR)
