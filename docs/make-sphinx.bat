del /Q .apidoc
sphinx-apidoc -o .apidoc ../pylablib
del /Q _build
make html