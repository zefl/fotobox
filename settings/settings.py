import json

class Settings(dict):
    ''' Settings gives an option to use json input as dict and via dot opertor
    This class holds metadata and overloading the get and set function makes use them
    Parent class dict holds the data -> key/value
    '''
    def __init__(self, **kwargs):
        self._metadata = dict(kwargs)
        self._callbacks = {}
        self._ret = json.dumps( {'return': 'error'} )

        if kwargs:
            for tag in kwargs:
                super().__setitem__(tag,kwargs[tag]['value'])

    def get_json(self):
        return self._metadata

    def __getitem__(self, key):
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        #Handle private variables seperatly
        if key.startswith('_'):
            super().__setitem__(key, value)
        else:
            if self._metadata[key]['min'] <= int(value) and int(value) <= self._metadata[key]['max']:
                self._value = value
                if key in self._callbacks:
                    self._ret = self._callbacks[key](value)
                else: 
                    self._ret = {'return': 'okay'}
                if self._ret['return'] == 'okay':
                    self._metadata[key]['value'] = value
                    super().__setitem__(key, value)

    def __getattr__(self, attr):
        return self.__getitem__(attr)

    def __setattr__(self, key, value):
        #Handle private variables seperatly
        if key.startswith('_'):
            self.__setitem__(key, value)
        else:
            if self._metadata[key]['min'] <= int(value) and int(value) <= self._metadata[key]['max']:
                self.__setitem__(key, value)
                # self._value = value
                # if key in self._callbacks:
                #     self._ret = self._callbacks[key](value)
                # else: 
                #     self._ret = json.dumps( {'return': 'okay'} )
                # if self._ret['return'] == 'okay':
                #     self.__setitem__(key, value)

    def Callback(self, key):
        def inner(func):
            self._callbacks[key] = func
        return inner
    
    def SetItemOkay(self):
        return self._ret