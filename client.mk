
VERSION=0.5.3
NAME=distilclient
INSTALL_PATH=/usr/lib/python2.7/dist-packages/distilclient
BINARY_PATH=/usr/local/bin

WORK_DIR=./work-client

CONF_DIR=${WORK_DIR}/${INSTALL_PATH}/etc/distil

clean:
	@rm -rf ${WORK_DIR}
	@rm -f ${NAME}_*.deb

init:
	@mkdir -p ${WORK_DIR}
	@mkdir -p ${WORK_DIR}${INSTALL_PATH}
	@mkdir -p ${WORK_DIR}${BINARY_PATH}

deb: clean init
	@mkdir -p ${WORK_DIR}${INSTALL_PATH}
	@cp     ./bin/distil ${WORK_DIR}${BINARY_PATH}/distil
	@cp		-r ./client/*.py ${WORK_DIR}${INSTALL_PATH}/
	@cp		__init__.py ${WORK_DIR}${INSTALL_PATH}/
	@chmod 0755 ${WORK_DIR}${BINARY_PATH}/distil
	@fpm -s dir -t deb -n ${NAME} -v ${VERSION} \
	--depends python2.7 \
	--depends python-keystoneclient \
	--depends python-requests \
	--template-scripts  \
	--template-value install_path=${INSTALL_PATH} \
	-C ${WORK_DIR} \
	.
