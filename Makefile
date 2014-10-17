
VERSION=0.4.2
NAME=distil
INSTALL_PATH=/opt/stack/distil
BINARY_PATH=/opt/stack/distil

WORK_DIR=./work-api

CONF_DIR=${WORK_DIR}/${INSTALL_PATH}/etc/distil

clean:
	@rm -rf ${WORK_DIR}
	@rm -f ${NAME}_*.deb

init:
	@mkdir ${WORK_DIR}/
	@mkdir -p ${WORK_DIR}${INSTALL_PATH}
	@mkdir -p ${WORK_DIR}${BINARY_PATH}

deb: clean init

	@cp -r ./distil \
		./README.md \
		setup.py \
		${WORK_DIR}${INSTALL_PATH}
	@mkdir ${WORK_DIR}${INSTALL_PATH}/bin
	@cp     ./bin/web ./bin/web.py \
		${WORK_DIR}${INSTALL_PATH}/bin
	@chmod 0755 ${WORK_DIR}${INSTALL_PATH}/bin/web
	@mkdir -p ${CONF_DIR}
	@mkdir -p ${WORK_DIR}/etc/distil
	@cp ./examples/conf.yaml ${WORK_DIR}/etc/distil/conf.yaml
	@cp ./examples/real_rates.csv ${WORK_DIR}/etc/distil/real_rates.csv
	@fpm -s dir -t deb -n ${NAME} -v ${VERSION} \
	--config-files etc \
	--depends 'libpq-dev' \
	--depends 'libmysql++-dev' \
	--depends python2.7 \
	--depends python-pip \
	--depends python-dev \
	--depends python-virtualenv \
	--depends python-sqlalchemy \
	--depends python-keystoneclient \
	--depends python-requests \
	--depends python-flask \
	--depends python-novaclient \
	--depends python-decorator \
	--depends python-mysqldb \
	--depends python-psycopg2 \
	--depends python-yaml \
	--template-scripts  \
	--template-value install_path=${INSTALL_PATH} \
	-C ${WORK_DIR} \
	.
