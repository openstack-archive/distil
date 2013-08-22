cp /vagrant/sources.list /etc/apt/sources.list

rm /boot/grub/grub.cfg

grub-install --boot-directory=/boot /dev/sda
grub-setup -d /boot/grub /dev/sda

touch /etc/apt/apt.conf.d/00force_old_configs
sudo cat >> /etc/apt/apt.conf.d/00force_old_configs <<DELIM
DPkg::Options { "--force-confdef"; "--force-confold"; }
DELIM

wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
  apt-key add -

apt-key advanced --keyserver pgp.net.nz --recv-keys 621846D9

aptitude update

# aptitude -y upgrade
aptitude install -y mongodb mongodb-server git python-dev libxslt-dev libxml2-dev libffi-dev screen curl libmysqlclient-dev node-less vim
aptitude install -y python-pip

gem install fpm



# apt-get upgrade -y
dpkg -i /vagrant/python-netaddr_0.7.10_all.deb
dpkg -i /vagrant/python-pyparsing_1.5.7_all.deb
dpkg -i /vagrant/python-cmd2_0.6.5.1_all.deb
dpkg -i /vagrant/python-requests_1.2.3_all.deb

easy_install -U distribute

pip install mysql-python

# sudo /vagrant/devstack/stack.sh