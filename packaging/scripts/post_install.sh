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

# Set up the /usr/local/artifice-bill script

cat > /usr/local/bin/artifice-bill <<EOF
#!/bin/bash
<%=install_path%>/env/bin/python <%=install_path%>/bin/bill.py \$@

EOF

cat > /usr/local/bin/artifice-usage <<EOF
#!/bin/bash
<%=install_path%>/env/bin/python <%=install_path%>/bin/usage.py \$@
EOF

chmod 0755 /usr/local/bin/artifice-usage
chmod 0755 /usr/local/bin/artifice-bill

cp <%=install_path%>/etc/artifice/conf.yaml /etc/artifice/conf.yaml
cp <%=install_path%>/etc/artifice/database /etc/artifice/database
 chown 0644 /etc/artifice/database

