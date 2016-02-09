

class NoPickling(BaseException):
    """Should not be pickling"""


class NoPickle(object):

    def __init__(self, *args, **kwargs):
        pass

    def dump(self, value):
        raise NoPickling("Pickling is not allowed!")

    def load(self, value):
        raise NoPickling("Unpickling is not allowed!")
