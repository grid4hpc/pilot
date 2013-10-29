.. -*- encoding: utf-8 -*-

=============================================================
 Как установить и обновлять development-версию сервера pilot
=============================================================

:Автор:
  Шамардин Л.В.

:Версия:
  `$Rev$` от `$Date$`

.. contents:: Содержание:
  :depth: 3


Установка из RPM
================

Далее описываются процедуры, необходимые для установки, настройки и
обновления pilot из RPM-пакетов. Этот метод является рекомендованным
для тех, кто не занимается разработкой pilot, и хочет установить
сервер для обычной экпслуатации или тестирования.

Установка
---------

1. Подключить репозиторий dist-el5-testing (скачать
   http://koji.ngrid.ru/ngrid.repo в ``/etc/yum.repos.d`` и поставить
   ``enabled=1`` для ``ngrid-testing``)

2. ``yum install pilot``

3. Установить python-globusws по его инструкции.

4. Доустановить пакеты для БД и настроить БД (если необходимо).

   i) Если планируется использовать PostgreSQL, то установить пакет
      ``python-psycopg2``.

      * Завести пользователя и базу, например::
        
          [root@tb02 ~]# su - postgres
          -bash-3.2$ createuser -P pilot
          Enter password for new role: 
          Enter it again: 
          Shall the new role be a superuser? (y/n) n
          Shall the new role be allowed to create databases? (y/n) n
          Shall the new role be allowed to create more new roles? (y/n) n
          CREATE ROLE
          -bash-3.2$ createdb -O pilot pilot
          CREATE DATABASE
          -bash-3.2$ createlang plpgsql pilot

      * Разрешить md5-авторизацию в pg_hba.conf

   ii) Если планируется использовать SQLite, то установить
       ``python-sqlite2``.


       .. >= 2.3.5. Он есть в репозитории ngrid, но более старые
          версии есть в EPEL и RPMForge. Их необходимо заблокировать,
          добавив exclude=python-sqlite2 в epel.repo и rpmforge.repo

5. Отредактировать /etc/pilot/pilot.ini, прописав параметры соединения
   с базой данных (и исправив другие настройки при необходимости).

6. Инициализировать базу данных::

     pilot-manage-db -c /etc/pilot/pilot.ini version_control
     pilot-manage-db -c /etc/pilot/pilot.ini upgrade

7. Включить сервисы на автозапуск и запустить их::

     chkconfig --level 345 pilot-httpd on
     chkconfig --level 345 pilot-spooler on
     service pilot-httpd start
     service pilot-spooler start

Обновление
----------

Обновление производится обычным образом для RPM-пакетов. После
обновления необходимо обновить схему базы данных и перезапустить
сервисы. ::

     yum update pilot
     pilot-manage-db -c /etc/pilot/pilot.ini upgrade
     service pilot-httpd restart
     service pilot-spooler restart

Ручная установка
================

Ниже перечислены шаги, необходимые для установки development-версии
сервера pilot.

Предварительные требования
--------------------------

В системе должны быть установлены пакеты swig, python-devel,
python-setuptools, openssl-devel, sqlite-devel, а так же работающий
gcc и python-globusws.

Для установки понадобится 3 директории (имена могут быть изменены как угодно):

* ``pilot`` - директория, в котрой будет жить свежий исходный код
  pilot

* ``pilot_deploy`` - директория, в которой будет жить virtualenv с
  установленным сервером pilot

* ``pilot_var`` - директория, в которой будет жить база данных
  сервера, конфигурационный файл и т.д.

Настоятельно рекомендуется не производить установку под root.

Установка
---------

1. Скачать свежую версию pilot::
     
     svn co https://svn.ngrid.ru/pilot/trunk pilot

2. Установить внешние зависимости. Этот шаг можно сделать одним из
   двух способов:

   1. Через `PyPI <http://pypi.python.org/pypi>`_ (более медленный). 
   
   2. Через скрипт create_env.py (рассчитан на частое использование в
      процессе разработки). ::

        ./cli/create_env.py -d ../pilot_deploy

      Предупреждение: create_env.py полностью удаляет директорию,
      переданную ему в качестве аргумента в процессе работы.

3. Активировать virtualenv, установить pilot_cli и pilot::

     . ../pilot_deploy/bin/activate
     cd cli
     python setup.py install
     cd ..
     python setup.py install

4. Сгенерировать конфигурационный файл и rc-скрипт для pilot::

     mkdir ../pilot_var
     paster make-config pilot ../pilot_var/deploy.ini
     paster pilot_initscript -c ../pilot_var/deploy.ini ../pilot_var/pilot-rc.sh

   Если не планируется запускать сервис автоматически при загрузке
   системы, то при генерации rc-файла необходимо так же указать опции
   ``-p`` и ``-l``. (Запустите ``paster pilot_initscript --help`` для
   полного списка опций).

5. Отредактировать конфигурационный файл
   ``../pilot_var/deploy.ini``. Настоятельно рекомендуется проверить
   опции ``user``, ``group`` из секции ``[common]``, установить
   значения для ``[httpd]/error_log``, ``[spooler]/logfile``,
   ``[matchmaker]/*``. Для отладки так же рекомендуется установить
   ``[spooler]/debug_level = 4``. В значениях опций можно использовать
   строку ``%(here)s``, она будет заменена на путь к директории, в
   которой находится файл deploy.ini.

6. Инициализировать базу данных. ::

     paster setup-app ../pilot_var/deploy.ini

   Примечание: пункт устарел, инициализацию базы данных производить
   согласно описанию установки через RPM.

7. Если планируется автоматически запускать pilot при загрузке
   системы, то необходимо прописать rc-скрипт в систему (данные
   команды необходимо выполнять от ``root``)::

     cd /etc/init.d
     ln -s ...../pilot_var/pilot-rc.sh pilot
     chkconfig --add pilot
     chkconifg --level 345 pilot on

8. Запустить pilot. В зависимости от того, устанавливался ли он для
   запуска от root при загрузке системы или от обычного пользователя,
   выполнить либо ``/etc/init.d/pilot start`` от root, либо
   ``...../pilot_var/pilot-rc.sh start``.

9. Убедиться, что сервисы работают. В лог-файле ``[httpd]/error_log``
   должны присутствовать сообщения о запуске сервиса, в лог-файле
   ``[spooler]/logfile`` каждые несколько секунд должна появляться
   строка с информацией о потребляемой памяти. Кроме того, rc-скрипт с
   параметром status должен показывать, что сервисы работают.

Обновление
----------

Далее предполагается, что сервис pilot установлен для запуска от root
при старте системы. В случае, если он установлен для запуска
пользователем, меняется только способ остановки и запуска сервисов.

1. Обновите исходные тексты::

     cd pilot
     svn up

2. Остановите сервис pilot. От root::

     /etc/init.d/pilot stop

3. Активируйте virtualenv::

     . ../pilot_deploy/bin/activate

4. Установите свежие версии pilot_cli и pilot::

     cd cli
     python setup.py install
     cd ..
     python setup.py install

   Если вы получаете какие-либо сообщения об ошибках, возможно
   проблема в недоустановленных зависимостях. Выполните повторно пункт
   №2 инструкции по начальной установке.

5. При необходимости отредактируйте ``../pilot_var/deploy.ini``.

6. Обновите схему базы данных согласно инструкциям по установке из RPM.

7. Запустите сервис pilot и убедитесь, что все работает. От root::

     /etc/init.d/pilot start
     /etc/init.d/pilot status

8. Если сервис не запускается, наиболее вероятная причина - новые
   необходимые пункты в конфигурационном файле. Выполните шаги 4-5
   инструкции по начальной установке.
