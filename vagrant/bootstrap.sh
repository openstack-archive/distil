apt-get -y install language-pack-en aptitude


cat > /etc/apt/sources.list <<DELIM
deb http://ubuntu.catalyst.net.nz/ubuntu/ precise main restricted
deb-src http://ubuntu.catalyst.net.nz/ubuntu/ precise main restricted

deb http://ubuntu.catalyst.net.nz/ubuntu/ precise-updates main restricted
deb-src http://ubuntu.catalyst.net.nz/ubuntu/ precise-updates main restricted

deb http://ubuntu.catalyst.net.nz/ubuntu/ precise universe
deb-src http://ubuntu.catalyst.net.nz/ubuntu/ precise universe
deb http://ubuntu.catalyst.net.nz/ubuntu/ precise-updates universe
deb-src http://ubuntu.catalyst.net.nz/ubuntu/ precise-updates universe

deb http://ubuntu.catalyst.net.nz/ubuntu/ precise multiverse
deb-src http://ubuntu.catalyst.net.nz/ubuntu/ precise multiverse
deb http://ubuntu.catalyst.net.nz/ubuntu/ precise-updates multiverse
deb-src http://ubuntu.catalyst.net.nz/ubuntu/ precise-updates multiverse

deb http://ubuntu.catalyst.net.nz/ubuntu/ precise-backports main restricted universe multiverse
deb-src http://ubuntu.catalyst.net.nz/ubuntu/ precise-backports main restricted universe multiverse

deb http://security.ubuntu.com/ubuntu precise-security main restricted
deb-src http://security.ubuntu.com/ubuntu precise-security main restricted
deb http://security.ubuntu.com/ubuntu precise-security universe
deb-src http://security.ubuntu.com/ubuntu precise-security universe
deb http://security.ubuntu.com/ubuntu precise-security multiverse
deb-src http://security.ubuntu.com/ubuntu precise-security multiverse

deb http://debian.catalyst.net.nz/catalyst stable catalyst
deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main

DELIM


wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
  sudo apt-key add -

# apt-key advanced --keyserver pgp.net.nz --recv-keys 621846D9
sudo apt-key add - <<DELIM
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: PGP Key Server 0.9.6

mQGiBEOjrf4RBACLZuL7qc64U74TAcgzy78h+O6HsgGqwUB/FAQ8Mn7DQJpQdqwL
Of04rn/pp1e+gzVSllRz2fjqGWyIfm/9MucVMXbToRLfNQa23/zH0RDnF7aZfmtD
/kKs6E6OCz+YLz2aWNqSCx9Wr4ebjQWXEggwUnLigNSF2ZouvalACPTjswCgvmMJ
zMrWhg1kW+v8eIpq5gHObLkD/jHgyEdmmh5EGwsQhurdEPUoUY4q/EthC2+ItY0P
eGK5AHkMLofVVt/9NsSCCh8aMKTL5nZHaK0aGY2fB8zWPsQ6x7O3zTkta5zy1ZL1
6YzKnHN7l96RXY3PTMBB9mFD+3kPVzRxm0X/y9Lzz4UUkATAOpuG9Eiy5HYWsoXp
QYgFA/4zbm7AV0e5AMjgazdgi5LHayaJPZSsEoDQSeYwvh32IXscu/zedhy82MWM
MDxE99TT/UxFNMagzuI+ps3ZYgiRPpx+8lBkz3LIvxGm+M4Wq4LfKilhSvk0/rpD
rjvOOa/1x8J1rNuZPW+Q8VIVrTHF9e9mxignbjsyVMYCYflYI7Q9Q2F0YWx5c3Qg
RGViaWFuIFJlcG9zaXRvcnkgKFNpZ25pbmcpIDxtaXJyb3JAY2F0YWx5c3QubmV0
Lm56PohGBBARAgAGBQJDo68/AAoJEIyQNH+PBoASi98An1uWngyI1pRlkxzOHpW+
sFolR7FMAJ440lWwntv248RYoCuSmasW5szJroheBBMRAgAeAhsDBgsJCAcDAgMV
AgMDFgIBAh4BAheABQJHoOpaAAoJECyk7iliGEbZ+wcAoIQeKT4XRPLYaB7s8OVM
O3LQTC7FAJ9OgPLIxqw9yFYFvSuyF2XFU4mtBohkBBMRAgAkAhsDBgsJCAcDAgMV
AgMDFgIBAh4BAheABQJFnXXkBQkD+/DmAAoJECyk7iliGEbZIHoAn2w8sW4uo6vc
QXbOA6AFfXu5CW9CAKCrdP0zrIoIL+SqSlIQs/chDbLFgIhkBBMRAgAkBQJDo63+
AhsDBQkB9PoABgsJCAcDAgMVAgMDFgIBAh4BAheAAAoJECyk7iliGEbZtXoAoJ3F
+zlFFfQPJzLTCPPzeLStgb5NAJwPwuKN+zEERJoTlSr+Jim01WI5g7kCDQRDo64P
EAgAifZvsK+MjMaesf8mI8Ihp2/mjgdeIwRk9jfY5Pos2xdLP1pWm/Nt/pLMVv0c
WPCh2r/rccJ4914xRw4ueiIZRY18mibPfBoSBaS9IHyyQgRxB7RI+0XZOWoSZeJ/
8skwLbdBK5PQTaWh/zYm5gZatozcYkWSWVDgT+hIedjF/tIPO3O0RdqVU7Nb4ebn
QHxtTUS8sORW6OFc9ohSr08ZYNtb7sYvP5a1UIGrtXf31bic1fvH7VwxXH6DxzvW
GU4ptcEcstYwwQZi+8SMnb49MxYPuQpmr5O9HzmGScYEl7haqyKv3m3Q/QntoRnw
cgImzj7gBESDD497Pl/bAukLswADBgf/Uj8OUM4FcofTuS5dRnm2AGBLu0cjp7jO
lP6XEQJvfCrlDmY0MIzYrnemnKULkLCiB2TO3ZahD4ZnkYEe/AYsPqzORvTCwgQ0
2uVfp22Q9m0UtjaOA9jCLKD817GJybyW7nqQVzm65ZzQ+qbUSnQPcjJJdDlL4k49
QsxYJkImUeW9vQMC72xOiAJohyP1xEvboR8IR3ohPjvfw9d8zBRgLvKw4v8z0maC
xvMlBQWvAtAXfRL5kVaRQ8EMBRiIugh/JniKrfjlHEdBwqu5BzCCnCjXiE5gRdk8
v/BSQ9W2e6Gmi/kL+Y3hTBFgNdGaITlMyOxUVV3QRpPSfJ/zdR5wuohPBBgRAgAP
AhsMBQJFnXZIBQkD+/E5AAoJECyk7iliGEbZqbsAoJ/R0IrLIBaDHR2iolXqjNZ7
eaEcAJ9OD9sRuW0jFVzpTrGwyevw29zD8Q==
=IwIG
-----END PGP PUBLIC KEY BLOCK-----
DELIM
curl http://apt.puppetlabs.com/puppetlabs-release-precise.deb > /tmp/puppet.deb
sudo dpkg -i /tmp/puppet.deb

sudo apt-get update

apt-get install catalyst-keyring
apt-get -y update

sudo apt-get -y upgrade

apt-get -q -y -o DPkg::Options::=--force-confold install puppet gdebi
apt-get -y install language-pack-en # just to confirm
