
# This is simply a namespace for global config storage
main = None
export_config = None
auth = None
ceilometer = None
transformers = None


def setup_config(conf):
    global main
    main = conf['main']
    global export_config
    export_config = conf['export_config']
    global auth
    auth = conf['auth']
    global ceilometer
    ceilometer = conf['ceilometer']
    global transformers
    transformers = conf['transformers']
