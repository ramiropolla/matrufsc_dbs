DBs=20121.json 20122.json 20131.json 20132.json 20141.json 20142.json

all: $(DBs) $(addsuffix .gz,$(DBs))

clean::
	rm -f $(DBs) $(addsuffix .gz,$(DBs)) *~

%.json: py/parse_turmas.py db/%*.xml
	./$^ $@

%.gz: %
	gzip --best --no-name -c $< > $@

install: $(DBs) $(addsuffix .gz,$(DBs))
	cp $(DBs) $(addsuffix .gz,$(DBs)) $(DESTDIR)/
