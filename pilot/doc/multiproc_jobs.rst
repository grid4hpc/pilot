===========================
 Запуск параллельных задач
===========================

.. highlight:: python

Алгоритм подбора ресурсов и запуска
===================================

На запуск параллельных задач будут оказывать влияние следующие
атрибуты:

* :pilot:taskattr:`type`
* :pilot:taskattr:`count`
* :pilot:taskattr:`min_memory`

Подбор ресурсов для задачи осуществляется следующим
образом. Перебираются все сабкластеры:

#. Сабкластеры, для которых ``min_memory > Host.MainMemory.RAMSize``
   не рассматриваются.

#. Исключаются из рассмотрения все сабкластеры, не удовлетворяющие
   «понятным» :ref:`требованиям <jobsyntax-requirements>`.

#. Вычисляется количество машин в сабкластере. По хорошему надо-бы его
   публиковать, конечно::

     subcluster_hosts = LogicalCPUs / Host.Architecture.SMPSize

#. Рассчитывается максимальное количество процессов на машину, которые
   можно запустить для данной задачи::

     processes_per_host = min(math.floor(Host.MainMemory.RAMSize / min_memory), 
                              Host.Architecture.SMPSize)

#. Рассчитывается максимальное количество процессов задачи, которое
   может быть запущено на данном сабкластере::

     cluster_processes = processes_per_host * subcluster_hosts

#. Если ``cluster_processes >= count``, то ресурс считается
   подходящим, иначе ресурс считается не подходящим.

#. Рассчитывается ``host_count``::

     host_count = math.ceil(count / processes_per_host)

Таким образом находятся все подходящие сабкластеры.

При запуске задачи, результирующий Globus RSL зависит от LRMS
кластера.

Вне зависимости от типа кластера, для задач с :pilot:taskattr:`type`
== ``single``:

.. code-block:: xml

   ...
   <jobType>single</jobType>
   <count>1</count>
   ...


PBS
---

В зависимости от типа задачи:

:pilot:taskattr:`type` == ``mpi``:

  .. code-block:: xml

     ...
     <jobType>mpi</jobType>
     <count>count</count>
     <extensions>
       <resourceAllocationGroup>
         <hostCount>host_count</hostCount>
         <cpusPerHost>processes_per_host</cpusPerHost>
         <cpusCount>count</cpusCount>
         <processCount>count</processCount>
         <processesPerHost>processes_per_host</processesPerHost>
       </resourceAllocationGroup>
     </extensions>
     ...

:pilot:taskattr:`type` == ``openmp``:

  .. code-block:: xml

     ...
     <jobType>multiple</jobType>
     <count>count</count>
     <extensions>
       <resourceAllocationGroup>
         <hostCount>host_count</hostCount>
         <cpusPerHost>processes_per_host</cpusPerHost>
         <cpusCount>count</cpusCount>
         <processCount>count</processCount>
         <processesPerHost>processes_per_host</processesPerHost>
       </resourceAllocationGroup>
     </extensions>
     ...

Cleo
----

Нужно, чтобы кластер с Cleo дополнительно публиковал таблицу
соответствия :pilot:taskattr:`type` ↔ ``profile``. Дальше зная нужный
``profile``:

.. code-block:: xml

   ...
   <jobType>mpi или multiple (для openmp)</jobType>
   <count>count</count>
   <extensions>
     <resourceAllocationGroup>
       <profile>profile</profile>
       <hostCount>host_count</hostCount>
     </resourceAllocationGroup>
   </extensions>
   ...

Расширение атрибутов задачи
===========================

* .. pilot:taskattr:: min_memory
     :type: int

  Минимальный объем памяти на один процесс, при котором задача может
  быть запущена.

* .. pilot:taskattr:: type

  Тип задачи. Возможные значения:

  - ``single`` (значение по умолчанию). Обычная однопроцессорная
    задача. Использование этого типа одновременно с
    :pilot:taskattr:`count` > 1 является ошибкой.

  - ``mpi``. Задача, использующая MPI.

  - ``openmp``. Задача, испоьзующая OpenMP.


