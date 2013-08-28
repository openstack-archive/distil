cp /vagrant/sources.list /etc/apt/sources.list

wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
  apt-key add -

apt-key advanced --keyserver pgp.net.nz --recv-keys 621846D9

aptitude update

aptitude install gdebi-core

gdebi -n /vagrant/openstack-artifice_0.1_amd64.deb