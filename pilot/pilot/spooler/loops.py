# -*- encoding: utf-8 -*-

__singlestep__ = False

class forever:
    """
    Декоратор, выполняющий функцию до тех пор, пока она не выкинет
    StopIteration

    Если глобальный параметр __singlestep__ установлен в True, то
    функция будет вызвана ровно один раз. Используется для запуска
    тестов.
    """
    def __init__(self, function):
        self.function = function

    def __call__(self):
        if __singlestep__:
            return self.function()
        else:
            try:
                while True:
                    self.function()
            except StopIteration:
                return
