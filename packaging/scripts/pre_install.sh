#!/bin/sh

# Loads a SQL script into postgres that creates the artifice DB.
# Post-install script is going to load all the DB stuff via pythons



if [ -e <%=install_path%>/etc/artifice/database ]; then
    PASSWORD=`cat <%= install_path %>/etc/artifice/database`
else
    PASSWORD=`pwgen -s 16`
    mkdir -p <%=install_path%>/etc/artifice
    touch <%=install_path%>/etc/artifice/database
    chmod 0600 <%=install_path%>/etc/artifice/database
    echo $PASSWORD > <%= install_path %>/etc/artifice/database
fi



sudo -u postgres psql -d template1 <<EOF
CREATE DATABASE <%=pg_database%>;
\c <%=pg_database%>
CREATE EXTENSION btree_gist;
CREATE USER <%=pg_user%> WITH ENCRYPTED PASSWORD '$PASSWORD';
ALTER DATABASE <%=pg_database%> OWNER TO <%=pg_user%>;
EOF