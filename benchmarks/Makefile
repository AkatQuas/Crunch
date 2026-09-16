
benchmark:
	rm -rf img/.originals
	mkdir -p img/.originals
	cp img/*.png img/.originals/
	cd img && /usr/bin/time -p crunch *.png
	python3 bench.py
	rm -rf img/.originals


.PHONY: benchmark
