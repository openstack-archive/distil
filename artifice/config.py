
# This is simply a namespace for global config storage
main = None
rates_config = None
auth = None
ceilometer = None
collection = None
transformers = None


def setup_config(conf):
    global main
    main = conf['main']
    global rates_config
    rates_config = conf['rates_config']
    global auth
    auth = conf['auth']
    global ceilometer
    ceilometer = conf['ceilometer']
    global collection
    collection = conf['collection']
    global transformers
    transformers = conf['transformers']
