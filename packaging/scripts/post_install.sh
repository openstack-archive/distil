#!/bin/sh

PASSWORD=`cat <%= install_path %>/etc/artifice/database`


export DATABASE_URL="postgresql://<%= pg_user %>:$PASSWORD@localhost:<%=pg_port%>/<%=pg_database%>"

pip install virtualenv

# Set up a virtualenv for ourselves in this directory
virtualenv <%= install_path %>/env

# this should now be limited to only this space
<%=install_path%>/env/bin/pip install -r <%= install_path %>/requirements.txt
<%=install_path%>/env/bin/python <%= install_path %>/scripts/initdb.py

# And this. Woo.
<%=install_path%>/env/bin/python <%= install_path%>/setup.py install # register with python!