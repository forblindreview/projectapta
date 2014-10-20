
'''
   Classes that implement the Observer Design Pattern
   references Gamma E., Helm, R., Johnson, R., and Vlissides, J. Design 
   Patterns: Elements of Reusable Object-Oriented Software
'''
from org.python.core import PyObject

class Observable(PyObject):
    def __init__(self):
        self._observers = []

    def addObserver(self, observer):
        self._observers.append(observer)

    def removeObserver(self, observer):
        self._observers.remove(observer)   

    def notify(self):
        for observer in self._observers:
            observer.update()

class Observer(PyObject):
    def update(self, **kwargs):
       pass

