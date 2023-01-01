import os

class File:

    def __init__(self, directory, filename):
        self.directory = directory
        self.filename = directory + '/' + filename

    def create(self):
        try:
            if not os.path.exists(self.directory):
                os.mkdir(self.directory)
            
            fs = open(self.filename, mode='w')
            fs.close()
            return True

        except IOError:
            return None
    
    def putInFile(self, content):
        fs = open(self.filename, mode='w')
        fs.write(content)
        fs.close()
