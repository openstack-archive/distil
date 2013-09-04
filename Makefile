
VERSION=0.1
NAME=openstack-artifice
INSTALL_PATH=/opt/stack/artifice
BILLING_PROGRAM=bill.py
BINARY_PATH=/usr/local/bin

CONF_DIR=./work/${INSTALL_PATH}/etc/artifice

clean:
	@rm -rf ./work
	@rm -f *.deb

init:
	@mkdir ./work/
	@mkdir -p ./work${INSTALL_PATH}
	@mkdir -p ./work${BINARY_PATH}

deb: clean init

	@cp -r ./bin ./artifice ./scripts ./README.md ./INVOICES.md \
		requirements.txt setup.py ./work/${INSTALL_PATH}
	@mkdir -p ${CONF_DIR}
	@cp ./examples/conf.yaml ${CONF_DIR}
	@cp ./examples/csv_rates.yaml ${CONF_DIR}
	@ln -s ./work${INSTALL_PATH}/bin/${BILLING_PROGRAM} ./work${BINARY_PATH}/artifice-bill
	@fpm -s dir -t deb -n ${NAME} -v ${VERSION} \
	--pre-install=packaging/scripts/pre_install.sh   \
	--post-install=packaging/scripts/post_install.sh  \
	--deb-pre-depends postgresql-9.2  \
	--deb-pre-depends postgresql-server-dev-9.2 \
	--deb-pre-depends postgresql-contrib-9.2 \
	--deb-pre-depends pwgen \
	--deb-pre-depends python2.7 \
	--deb-pre-depends python-pip \
	--deb-pre-depends python-dev \
	--template-scripts  \
	--template-value pg_database=artifice  \
	--template-value pg_user=artifice  \
	--template-value pg_port=5432  \
	--template-value install_path=${INSTALL_PATH} \
	-C ./work \
	.