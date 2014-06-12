
VERSION=0.1
NAME=openstack-distil
INSTALL_PATH=/opt/stack/distil
BILLING_PROGRAM=bill.py
BINARY_PATH=/usr/local/bin

WORK_DIR=./work

CONF_DIR=${WORK_DIR}/${INSTALL_PATH}/etc/distil

clean:
	@rm -rf ./work
	@rm -f *.deb

init:
	@mkdir ./work/
	@mkdir -p ./work${INSTALL_PATH}
	@mkdir -p ./work${BINARY_PATH}

deb: clean init

	@cp -r ./distil \
		./scripts \
		./README.md \
		./INVOICES.md \
		requirements.txt \
		setup.py \
		${WORK_DIR}${INSTALL_PATH}
	@mkdir ${WORK_DIR}${INSTALL_PATH}/bin
	@cp ./bin/collect ./bin/collect.py \
		./bin/usage ./bin/usage.py \
		./bin/web ./bin/web.py \
		${WORK_DIR}${INSTALL_PATH}/bin
	@chmod 0755 ${WORK_DIR}${INSTALL_PATH}/bin/web
	@cp -r ./packaging/fs/* ${WORK_DIR}/
	@mkdir -p ${CONF_DIR}
	@mkdir -p ${WORK_DIR}/etc/init.d
	@mkdir -p ${WORK_DIR}/etc/distil
	@chmod +x ${WORK_DIR}/etc/init.d/distil
	@cp ./examples/conf.yaml ${WORK_DIR}/etc/distil/conf.yaml
	@cp ./examples/csv_rates.yaml ${WORK_DIR}/etc/distil/csv_rates.yaml
	@fpm -s dir -t deb -n ${NAME} -v ${VERSION} \
	--post-install=packaging/scripts/post_install.sh  \
	--depends 'libpq-dev' \
	--deb-pre-depends "libmysql++-dev" \
	--deb-pre-depends python2.7 \
	--deb-pre-depends python-pip \
	--deb-pre-depends python-dev \
	--deb-pre-depends python-virtualenv \
	--template-scripts  \
	--template-value install_path=${INSTALL_PATH} \
	-C ${WORK_DIR} \
	.
