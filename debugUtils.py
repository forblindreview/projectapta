''' 
  Utility decorators for printing debug statements
  source: http://code.sweyla.com/articles/python/decorators/
'''
import sys, traceback

class printdebug(object):
    '''
    A decorator that augments functions to print
    '''
    def __init__(self, arg=0):
        self.debug_level = arg
    def __call__(self, f):
        def newf(*args, **kwargs):
            frame = traceback.extract_stack()[-2]
            if self.debug_level > 0: print 'DEBUG: Entering ', frame[3]
            c = f(*args, **kwargs)
            print "Function returned %s and used argument %s" % (c, self.debug_level)
            if self.debug_level > 0: print 'DEBUG: Exiting ', frame[3]
            return c
        return newf

def main():
    @printdebug(1)
    def foo(a, b):
        return a**b
    foo(10,3)

if __name__ == '__main__':
    main()

