init:
	pip3 install -r dev/requirements.txt

test:
	pylint pydoc_ext/
	eval "PYTHONPATH=`pwd` py.test -v --doctest-modules --flake8 tests/ pydoc_ext/"

run_ul:
	ulauncher --no-extensions --dev -v

run:
	VERBOSE=1 ULAUNCHER_WS_API=ws://127.0.0.1:5054/com.github.pbkhrv.ulauncher-pydoc PYTHONPATH=/usr/lib/python3/dist-packages /usr/bin/python3 `pwd`/main.py

symlink:
	rm -rf ~/.local/share/ulauncher/extensions/com.github.pbkhrv.ulauncher-pydoc
	ln -s `pwd` ~/.local/share/ulauncher/extensions/com.github.pbkhrv.ulauncher-pydoc

unlink:
	rm -rf ~/.local/share/ulauncher/extensions/com.github.pbkhrv.ulauncher-pydoc
