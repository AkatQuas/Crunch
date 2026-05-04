VENV := .venv
VENV_ACTIVATE := $(VENV)/bin/activate

# Create virtual environment only if it does NOT exist
$(VENV_ACTIVATE):
	uv venv

# Build targets
build-dependencies:
	src/install-dependencies.sh
	cp ~/.local/bin/pngquant ./src/include
	cp ~/.local/bin/zopflipng ./src/include

build-macos-icns:
	rm -rf img/CrunchIcon.iconset
	mkdir img/CrunchIcon.iconset
	sips -z 16 16     img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_16x16.png
	sips -z 32 32     img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_16x16@2x.png
	sips -z 32 32     img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_32x32.png
	sips -z 64 64     img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_32x32@2x.png
	sips -z 128 128   img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_128x128.png
	sips -z 256 256   img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_128x128@2x.png
	sips -z 256 256   img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_256x256.png
	sips -z 512 512   img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_256x256@2x.png
	sips -z 512 512   img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_512x512.png
	sips -z 1024 1024   img/Crunch-icon-3.png --out img/CrunchIcon.iconset/icon_512x512@2x.png
	cd img && iconutil -c icns CrunchIcon.iconset

build-macos-installer: ## create fast dmg during development
	# https://github.com/sindresorhus/create-dmg
	-rm bin/*.dmg
	-cd bin && npx -y create-dmg --no-code-sign Crunch.app
	# create checksum file for the installer
	cd bin && mv Crunch*.dmg Crunch-Installer.dmg
	cd bin && shasum -a 256 Crunch-Installer.dmg > Crunch-Installer-checksum.txt
	open bin

# Install targets
install-python-deps: $(VENV_ACTIVATE)
	uv pip install -r requirements.txt

install-executable:
	mkdir -p ~/.local/bin
	cp src/crunch.py ~/.local/bin/crunch
	@echo " "
	@echo "[*] crunch executable installed on path ~/.local/bin/crunch"
	@echo "[*] Usage: $ crunch [options] [image path 1]...[image path n]"

install-macos-service:
	- sudo rm -rf ~/Library/Services/Crunch\ Image\(s\).workflow
	sudo cp -R service/Crunch\ Image\(s\).workflow ~/Library/Services/Crunch\ Image\(s\).workflow
	@echo " "
	@echo "[*] Crunch Image(s) macOS service installed on the path ~/Library/Services/Crunch\ Image\(s\).workflow"
	@echo " "
	@echo "[*] You can use the Crunch service by right clicking on one or more PNG files, then select Services > Crunch Image(s)"

uninstall-executable:
	rm ~/.local/bin/crunch
	@echo " "
	@echo "[*] crunch executable uninstall complete."

uninstall-macos-service:
	sudo rm -rf ~/Library/Services/Crunch\ Image\(s\).workflow
	@echo " "
	@echo "[*] The Crunch Image(s) macOS service was removed from your system"

# Test targets
test-coverage:
	./coverage.sh

test-python: $(VENV_ACTIVATE)
	. .venv/bin/activate && tox && black --check src/crunch.py

test-shell: $(VENV_ACTIVATE)
	. .venv/bin/activate && shellcheck --exclude=2046 src/*.sh

test-valid-png-output:
	crunch testfiles/*.png
	pngcheck testfiles/*-crunch.png
	rm testfiles/*-crunch.png

test: test-coverage test-python test-shell test-valid-png-output

# Utility targets
clean:
	rm benchmarks/img/*-crunch.png

benchmark:
	cd benchmarks && $(MAKE) $@

dist:
	./dmg-builder.sh

dist-homebrew:
	cask-repair crunch


.PHONY: benchmark build-dependencies build-macos-icns build-macos-installer install-python-deps install-executable install-macos-service uninstall-dependencies uninstall-executable uninstall-macos-service test test-coverage test-python test-shell test-valid-png-output dist dist-homebrew clean
