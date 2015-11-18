SOURCE_DIR ?= ctf_gameserver/web
EXT_DIR ?= $(SOURCE_DIR)/static/ext

.PHONY: all db lint
.INTERMEDIATE: bootstrap.zip

all: db $(EXT_DIR)/jquery.min.js $(EXT_DIR)/bootstrap $(SOURCE_DIR)/registration/countrynames.txt


# Cannot use `$(SOURCE_DIR)/dev-db.sqlite3` as target name since the database might be different from the
# SQLite file
db:
	./manage.py migrate auth
	./manage.py migrate

$(EXT_DIR)/jquery.min.js:
	mkdir -p $(EXT_DIR)
	curl https://code.jquery.com/jquery-1.11.3.min.js -o $@

bootstrap.zip:
	curl -L https://github.com/twbs/bootstrap/releases/download/v3.3.5/bootstrap-3.3.5-dist.zip -o $@

$(EXT_DIR)/bootstrap: bootstrap.zip
	mkdir -p $(EXT_DIR)
	unzip -n $< -d $(EXT_DIR)
	mv -v $(EXT_DIR)/bootstrap-3.3.5-dist $(EXT_DIR)/bootstrap

$(SOURCE_DIR)/registration/countrynames.txt:
	curl http://www.opengeocode.org/download/countrynames.txt -o $@


lint:
	# Run Pylint and pep8 to check the code for potential errors and style guideline violations, but ignore
	# their exit codes
	-pylint $(SOURCE_DIR)
	-pep8 --max-line-length=109 $(SOURCE_DIR)
