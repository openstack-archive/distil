#!/bin/sh

PASSWORD=`cat <%= install_path %>/etc/artifice/database`


export DATABASE_URL="postgresql://<%= pg_user %>:$PASSWORD@localhost:<%=pg_port%>/<%=pg_database%>"

pip install -r <%= install_path %>/requirements.txt

python <%= install_path %>/scripts/initdb.py

python <%= install_path%>/setup.py install # register with python!