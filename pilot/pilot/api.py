# -*- encoding: utf-8 -*-

from zope.interface import Interface, Attribute, Invalid, invariant


__all__ = [
    'APIError',
    'IHTTPConsumer',
    'IResourceEnumerator', 'ICachingResourceEnumerator',
    'IResource', 'IResourceConfiguration', 'IResourceState',
    'IResourceSoftware', 'ISubmissionParameters', 'ITaskState',
    'ITaskExecutor', 'TaskExecutorError', 'FatalTaskExecutorError',
    'NonFatalTaskExecutorError', 'TimeoutTaskExecutorError',
    ]


class APIError(Invalid): pass


class IResourceEnumerator(Interface):
    u"""
    Интерфейс предоставления информации о ресурсах
    """

    timeout = Attribute(u"Максимальная длительность одного запроса "
                        u"к внешнему сервису")

    def enumerate():
        u"""
        Возвращает генератор или последовательность доступных ресурсов
        в виде объектов с интерфейсом IResource.
        """

def fetch_url_is_set(self):
    if self.fetch_url is None:
        raise APIError("fetch_url is not set")

class IHTTPConsumer(Interface):
    u"""
    Объекты с этим интерфейсом требуют внешней функции fetch_url для
    отправки HTTP-запросов:

    fetch_url(url, method='GET', body=None, extra_headers={}, timeout=None)

    Возвращает тройку значений (content, status, headers), где status
    - HTTP-код ответа, headers - dict с заголовками ответа

    В случае таймаута, функция должна отвечать ошибкой 504 не вызывая
    исключений.
    
    """

    fetch_url = Attribute(u"функция fetch_url (см. описание интерфейса)")

    invariant(fetch_url_is_set)
        

class ICachingResourceEnumerator(IResourceEnumerator):
    u"""
    Поставщик информации о ресурсах, поддерживающий кеширование
    """

    def stale():
        u"""Возвращает True, если информация о ресурсах нуждается в обновлении"""

    def refresh():
        u"""Обновляет кеш информации о ресурсах"""

class IResource(Interface):
    u"""Вычислительный ресурс"""

    hostname = Attribute(u"Имя хоста")
    port = Attribute(u"порт")
    lrms = Attribute(u"Тип локального менеджера ресурсов")
    queue = Attribute(u"название очереди")
    version = Attribute(u"Версия GRAM/локельного менеджера и т.п.")

    config = Attribute(u"Конфигурация вычислительного ресурса "
                       u"(объект с интерфейсом IResourceConfiguration)")
    software = Attribute(u"Список предустановленного программного обеспечения "
                         u"(объекты с интерфейсом IResourceSoftware)")

    state = Attribute(u"Состояние ресусра "
                      u"(объект с интерфейсом IResourceState")

    def access_allowed(fqans):
        u"""
        fqans - список VOMS FQAN, используемых для доступа к ресурсу

        Возвращает True, если такой набор FQAN потенциально позволяет
        запускать задачи на данном ресурсе.
        """


class IResourceConfiguration(Interface):
    u"""Конфигурация вычислительного ресурса"""

    os_name = Attribute(u"Название операционной системы")
    os_release = Attribute(u"Релиз операционной системы")
    os_version = Attribute(u"Версия операционной системы")

    platform = Attribute(u"Архитектура процессоров")
    smp_size = Attribute(u"Число логических процессорных ядер на одном узле")
    cpu_hz = Attribute(u"Частота процессора")
    cpu_instruction_set = Attribute(u"Набор инструкций процессора")
    cpu_model = Attribute(u"Модель процессора")
    ram_size = Attribute(u"Объем оперативной памяти одного узла")
    virtual_size = Attribute(u"Объем виртуальной памяти одного узла")

    physical_slots = Attribute(u"Число узлов в кластере")
    physical_cpus = Attribute(u"Число процессоров (физических)")
    logical_cpus = Attribute(u"Число процессорных ядер "
                             u"(с учтеом hyperthreading и т.п.)")


class IResourceState(Interface):
    u"""Состояние вычислительного ресурса"""

    total_cpus = Attribute(u"Число логических процессорных ядер, "
                           u"фактически подключенных к кластеру")
    free_cpus = Attribute(u"Число свободных логических процессорных ядер")

    running_jobs = Attribute(u"Число выполняющихся задач")
    total_jobs = Attribute(u"Общее число задач, так или иначе "
                           u"обрабатывающихся кластером")
    waiting_jobs = Attribute(u"Число задач в очереди на выполнение")

    enabled = Attribute(u"Разрешено ли выполнение задач")


class IResourceSoftware(Interface):
    u"""Пакет с программным обеспечением"""
    
    name = Attribute(u"Название пакета ПО")
    version = Attribute(u"Версия пакета ПО "
                        u"(объект класса distutils.version.LooseVersion)")

    def activate(task_definition):
        u"""
        Модифицировать описание задачи (dict) таким образом, чтобы
        можно было использовать данный пакет ПО. Изменяет
        task_definition.
        """
        

class ISubmissionParameters(Interface):
    u"""Параметры запуска задачи"""

    description = Attribute(u"Сериализованное в строку описание задачи, "
                            u"понимаемое данной системой запуска задач.")
    arguments = Attribute(u"Параметры командной строки (список строк) "
                          u"для команды запуска задачи")
    id = Attribute(u"Короткий идентификатор задачи (опциональный)")


class ITaskState(Interface):
    u"""Состояние задачи"""

    state = Attribute(u"Состояние задачи (строка). "
                      u"Возможные значения: unknown, pending, running, "
                      u"finished, aborted")
    reason = Attribute(u"Причина, вызвавшая данное состояние "
                       u"(строка, для человека)")
    exit_code = Attribute(u"Код выхода задачи (число). Обязан иметь "
                          u"значение только для состояния finished")


class ITaskExecutor(Interface):
    u"""Исполнитель задач"""

    def get_submission_parameters(task_definition, resource):
        u"""
        task_definition - описание задачи (dict)
        resource - ресурсв (IResource)

        Возвращает параметры запуска задачи (ISubmissionParameters) с
        таким описанием на ресурсе resource.
        """

    def submit(parameters, proxy):
        u"""
        parameters - параметры запуска задачи (ISubmissionParameters)
        proxy - цепочка прокси-сертификатов пользователя
                (строка, содержащая все сертификаты и ключи в формате PEM)

        Возвращает сериализованный в строку идентификатор, необходимый
        для проверки состояния выполнения задачи.
        """

    def status(taskid, proxy):
        u"""
        taskid - сериализованный в строку идентификатор задачи.
        proxy - цепочка прокси-сертификатов пользователя
                (строка, содержащая все сертификаты и ключи в формате PEM)

        Возвращает состояние задачи (ITaskState)
        """

    def kill(taskid, proxy):
        u"""
        taskid - сериализованный в строку идентификатор задачи.
        proxy - цепочка прокси-сертификатов пользователя
                (строка, содержащая все сертификаты и ключи в формате PEM)

        Отменить выполнение задачи.
        """

class TaskExecutorError(RuntimeError):
    u"""
    Базовый класс исключений ITaskExecutor
    """
    
class FatalTaskExecutorError(TaskExecutorError):
    u"""
    Фатальные ошибки. При возникновении такой ошибки выполнение требуемой
    операции невозможно.
    """
    
class NonFatalTaskExecutorError(TaskExecutorError):
    u"""
    Не фатальные ошибки. В данный момент операцию выполнить не удалось, однако,
    возможно, ее удастся выполнить позднее, или используя другой ресурс.
    """

class TimeoutTaskExecutorError(NonFatalTaskExecutorError):
    u"""
    Выполнение операции оборвалось по таймауту.
    """
