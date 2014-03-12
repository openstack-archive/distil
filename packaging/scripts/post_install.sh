#!/bin/sh

# PASSWORD=`cat <%= install_path %>/etc/artifice/database`

# pip install virtualenv

mkdir /var/run/artifice

# Set up a virtualenv for ourselves in this directory
virtualenv <%= install_path %>/env

# First, install an up-to-date pip into the virtualenv, since this is ridiculously ancient

<%=install_path%>/env/bin/pip install --upgrade pip

# Now iterate our requirements
# this should now be limited to only this space
<%=install_path%>/env/bin/pip install -r <%= install_path %>/requirements.txt
# And this. Woo.

cd <%=install_path%>
sudo ./env/bin/python ./setup.py install # register with python!


# Set up the artifice control scripts 

cat > /usr/local/bin/artifice-bill <<EOF
#!/bin/bash
<%=install_path%>/env/bin/python <%=install_path%>/bin/collect.py \$@

EOF

cat > /usr/local/bin/artifice-usage <<EOF
#!/bin/bash
<%=install_path%>/env/bin/python <%=install_path%>/bin/usage.py \$@
EOF

chmod 0755 /usr/local/bin/artifice-usage
chmod 0755 /usr/local/bin/artifice-bill

# cp <%=install_path%>/etc/artifice/conf.yaml /etc/artifice/conf.yaml
# cp <%=install_path%>/etc/artifice/database /etc/artifice/database
 # chown 0644 /etc/artifice/database

