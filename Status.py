class Status:
    def _displayMessage(self, message, level = None):
        # This can be modified easily
        if level is not None:
            print ("[%s] %s [%s]" % (level, message,level))
        else:
            print ("[default] %s" % (message))

    def debug(self, message):
        self._displayMessage(message, level = "###")
    def info(self, message):
        self._displayMessage(message, level = "---")