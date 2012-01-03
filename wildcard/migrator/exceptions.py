class MissingObjectException(Exception):

    def __init__(self, path):
        super(MissingObjectException, self).__init__()
        self.path = path
