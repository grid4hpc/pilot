# -*- encoding: utf-8 -*-

from cStringIO import StringIO
import datetime
import eventlet
import logging
import os
from subprocess import Popen, PIPE
import tempfile

from M2Crypto import RSA, SSL, X509
import pytz
import sqlalchemy as sa

from gridproxy import voms
from pilot import model
from pilot.lib import certlib, etree
from pilot.spooler import config, globus
from pilot.model.meta import Session
from pilot_cli import proxylib
from pilot_cli.httplib2m2 import Http

from loops import forever
import queues

log = logging.getLogger(__name__)
heartbeat = logging.getLogger(u"heartbeat." + __name__)

@forever
def loop():
    u"""
    Основной цикл обновления делегаций
    """
    heartbeat.debug("start")
    now = datetime.datetime.utcnow()
    should_renew = now + datetime.timedelta(seconds=config["delegations_renew_threshold"])
    delegations = Session.query(model.Delegation) \
        .filter(sa.and_(model.Delegation.renewable==True,
                        model.Delegation.myproxy_server != None,
                        model.Delegation.next_expiration < should_renew,
                        model.Delegation.next_expiration > now))
    for d in delegations:
        log.debug("Need to renew: %s, now=%s, should_renew=%s", d, now, should_renew)
        renew_delegation(d)
    heartbeat.debug("end")

    for t in Session.query(model.Task).filter_by(delegation_update_required=True):
        if t.state.s != u"running":
            t.delegation_update_required = False
            log.debug("%s: delegation update is no longer required: task is not running", t.logname())
            continue
        # XXX вообще говоря, надо тут проверять native_type
        if t.delegation_native_id is None:
            try:
                t.delegation_native_id = wsgram_get_delegation_id(t)
                if t.delegation_native_id is None:
                    log.error("%s: failed to get delegation native id", t.logname())
                    continue
            except Exception, exc:
                log.error("%s: exception while trying to get delegation native id: %s", t.logname(), str(exc))
                continue
        try:
            globus.credential_refresh(t.delegation_native_id, t.job.delegation.as_proxy())
            t.delegation_update_required = False
            Session.flush()
            log.debug("%s: delegation was refreshed.", t.logname())
        except globus.GlobusError, exc:
            log.error("%s: failed to refresh delegation: %s", t.logname(), str(exc))
            continue

    try:
        queues.delegations.get(True, config["delegations_loop"])
        while not queues.delegations.empty():
            queues.delegations.get()
    except eventlet.queue.Empty:
        pass


def check_host_proxy():
    u"""
    Проверить существование host proxy, обновить при необходимости

    Возвращает True в случае успеха или False в случае ошибки.
    """
    proxy_filename = config["host_proxy_filename"]
    try:
        key, chain = certlib.load_proxy(open(proxy_filename, "r").read())
        min_not_after = min(cert.get_not_after().get_datetime() for cert in chain)
        if min_not_after - datetime.datetime.now(pytz.UTC) > datetime.timedelta(seconds=300):
            log.debug("check_host_proxy: proxy is still valid")
            return True
    except IOError, exc:
        pass

    try:
        rsa, pkey = proxylib.generate_keypair()
        hostcert = X509.load_cert(config.common_ssl_certificate)
        hostkey = RSA.load_key(config.common_ssl_privatekey)
        cert = proxylib.generate_proxycert(pkey, hostcert, hostkey, full=True)
        hostproxy = os.open(proxy_filename, os.O_CREAT|os.O_TRUNC|os.O_WRONLY, 0600)
        os.chmod(proxy_filename, 0600)
        os.write(hostproxy, cert.as_pem())
        os.write(hostproxy, rsa.as_pem(cipher=None))
        os.write(hostproxy, hostcert.as_pem())
        os.close(hostproxy)
        log.debug("check_host_proxy: host proxy refreshed")
        return True
    except IOError, exc:
        log.debug("check_host_proxy: failed to refresh host proxy: %s", str(exc))
        return False

def renew_delegation(delegation):
    u"""
    Попытаться обновить делегацию через соответствущий myproxy сервер
    """
    proxy_file = tempfile.NamedTemporaryFile()
    proxy_file.write(delegation.as_proxy())
    proxy_file.flush()
    renew_cmd = ["myproxy-logon", "--dn_as_username", "--no_passphrase",
                 "--quiet", "--out", "-", "-a", proxy_file.name,]
    if ':' in delegation.myproxy_server:
        host, port = delegation.myproxy_server.split(':')
        renew_cmd.extend(["-s", host, "-p", port])
    else:
        renew_cmd.extend(["-s", delegation.myproxy_server])

    if delegation.credname is not None:
        renew_cmd.extend(["-k", delegation.credname])

    env = os.environ.copy()
    env["X509_USER_PROXY"] = proxy_file.name
    mpl = Popen(renew_cmd, env=env, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    out, err = mpl.communicate(None)
    if mpl.returncode != 0:
        log.error("Failed to renew credentials: %s", err)
        return

    key, chain = certlib.load_proxy(out)
    not_after = min(cert.get_not_after().get_datetime() for cert in chain)
    now = datetime.datetime.now(pytz.UTC)
    validity = not_after - now
    validity_hours = validity.days * 24 + (validity.seconds / 3600)
    validity_minutes = (validity.seconds % 3600) / 60

    proxy_file.seek(0)
    proxy_file.truncate()
    proxy_file.write(out)
    proxy_file.flush()

    voms_cmd = ["voms-proxy-init", "-rfc", "-noregen",
                "-voms", "%s:%s" % (delegation.vo, delegation.voms_renew_fqan()),
                "-order", "/%s" % (delegation.vo),
                "-valid", "%d:%d" % (validity_hours, validity_minutes-5),
                "-out", proxy_file.name]
    env = os.environ.copy()
    env["X509_USER_PROXY"] = proxy_file.name
    vpl = Popen(voms_cmd, env=env, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=True)
    out, err = vpl.communicate(None)
    if vpl.returncode != 0:
        log.error("Failed to renew credentials: voms-proxy-init failed: %s", err + out)
        return

    # voms-proxy-init в обязательном порядке сделает unlink на
    # proxy_file, поэтому этот дексриптор останется висеть "в воздухе"
    # Однако, NamedTemporaryFile при закрытии proxy_file удалит его по
    # имени, поэтому за очистку можно не беспокоиться, но переоткрыть
    # файл придется.

    voms_proxy = open(proxy_file.name, "rb")
    key, chain = certlib.load_proxy(voms_proxy.read())
    voms_proxy.close()
    voms_ac = voms.VOMS(config.common_voms_dir, config.common_ssl_capath)
    certlib.load_voms_chain(voms_ac, chain)

    delegation.key = key
    delegation.chain = chain
    not_after = min(cert.get_not_after().get_datetime() for cert in chain)
    not_after = min(not_after, voms_ac.not_after)
    # отрезать TZ
    not_after = datetime.datetime(*not_after.timetuple()[:6])
    delegation.next_expiration = not_after
    Session.add(delegation)
    Session.flush()

    log.debug("Renewed %s: %s", delegation, str(delegation.chain[0].get_subject()))
    Session.flush()
    mark_dependent_tasks(delegation)

def mark_dependent_tasks(delegation):
    u"""
    Пометить задачи, зависящие от данной делегации, и находящиеся в
    состоянии running, как нуждающиеся в обновлении делегации.
    """

    # XXX
    # Совершенно "тупая" и медленная реализация. Однако, для эффективной
    # реализации надо бы перепланировать схему хранения "состояний" заданий
    # и задач, текущая невероятно осложняет запросы к базе данных.
    for job in delegation.jobs:
        if job.state.s == u"running":
            for task in job.tasks:
                if task.state.s == u"running":
                    log.debug("Marked task %s as delegation_update_required" % task.logname())
                    task.delegation_update_required = True
    Session.flush()


def wsgram_get_delegation_id(task):
    if task.native_id is None:
        log.error("%s: impossible to get delegation id for a task without a native id", task.logname())
        return None

    DS_NS = "http://www.globus.org/08/2004/delegationService"
    JDL_NS = "http://www.globus.org/namespaces/2008/03/gram/job/description"
    WSA_NS = "http://www.w3.org/2005/08/addressing"

    try:
        props = globus.wsrf_query_epr(task.native_id, task.job.delegation.as_proxy())
    except globus.GlobusError, exc:
        log.error("%s: failed to query globus job properties, delegation not renewed: %s",
                  task.logname(), str(exc))
        return None

    sce = props.find("//{http://www.globus.org/namespaces/2008/03/gram/job/description}stagingCredentialEndpoint")
    if sce is None:
        log.error("%s: stagingCredentialEndpoint not found, delegation not renewed.", task.logname())
        return None

    epr = etree.Element("{http://www.w3.org/2005/08/addressing}EndpointReference")
    for elt in sce:
        epr.append(elt)

    dk = epr.find(".//{http://www.globus.org/08/2004/delegationService}DelegationKey")
    dk.attrib.clear()

    buf = StringIO()
    etree.ElementTree(epr).write(buf)
    return buf.getvalue()

