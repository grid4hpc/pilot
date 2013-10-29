"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from pylons import config
from routes import Mapper

def make_map():
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE
    map.connect('jobs', '/jobs', controller='job',
                conditions=dict(method=['GET']), action='index')
    map.connect('/jobs/', controller='job',
                conditions=dict(method=['GET']), action='index')
    map.connect('/jobs', controller='job',
                conditions=dict(method=['POST']), action='create')
    map.connect('/jobs/', controller='job',
                conditions=dict(method=['POST']), action='create')
    map.connect('job', '/jobs/{jid}/', controller='job',
                conditions=dict(method=['GET']), action='show')
    map.connect('/jobs/{jid}/', controller='job',
                conditions=dict(method=['PUT']), action='update')
    map.connect('/jobs/{jid}/', controller='job',
                conditions=dict(method=['DELETE']), action='delete')

    map.connect('task', '/jobs/{jid}/{task_name}/', controller='task',
                conditions=dict(method=['GET']), action='index')
    map.connect('/jobs/{jid}/{task_name}', controller='task',
                conditions=dict(method=['GET']), action='index')
    map.connect('/jobs/{jid}/{task_name}/', controller='task',
                conditions=dict(method=['PUT']), action='update')
    map.connect('/jobs/{jid}/{task_name}', controller='task',
                conditions=dict(method=['PUT']), action='update')
    
    map.connect('job_policy', '/policy/job/', controller='template',
                action='view', url=None)

    map.connect('version', '/version', controller='version',
                action='index')

    ########################## V2 API ##########################
    map.connect('state', '/gram-state-notification/{submission_id}', controller='task',
                conditions=dict(method=['POST']), action='add_state')

    map.connect('resources', '/v2/jobs/{jid}/resources',
                controller='job',
                conditions={'method':['GET']},
                action='matchmake')
    map.connect('/v2/jobs/{jid}/resources/',
                controller='job',
                conditions={'method':['GET']},
                action='matchmake')
    map.connect('rsl', '/v2/jobs/{jid}/RSL',
                controller='job',
                conditions={'method':['GET']},
                action='get_rsl')
    map.connect('/v2/jobs/{jid}/RSL/',
                controller='job',
                conditions={'method':['GET']},
                action='get_rsl')

    map.connect('accounting_period', '/v2/accounting/period/{ts1}-{ts2}/',
                controller='accounting',
                conditions={'method':['GET']},
                action='get_period')
    map.connect('/v2/accounting/period/{ts1}-{ts2}',
                controller='accounting',
                conditions={'method':['GET']},
                action='get_period')
    map.connect('accounting_last', '/v2/accounting/last/{records_count}/',
                controller='accounting',
                conditions={'method':['GET']},
                action='get_last')
    map.connect('/v2/accounting/last/{records_count}',
                controller='accounting',
                conditions={'method':['GET']},
                action='get_last')

    map.connect('resource_view', '/v2/resource_view', controller='resource_view',
                action='index')
    map.connect('resource_index', '/v2/resource_index', controller='resource_view',
                action='index2')

    map.connect('delegations', '/delegations', controller='delegations', action='index')
    map.connect('delegation', '/delegations/{delegation_id}',
                controller='delegations',
                conditions={'method':['GET']},
                action='get')
    map.connect('/delegations/{delegation_id}',
                controller='delegations',
                conditions={'method':['PUT']},
                action='create_or_update')
    map.connect('delegation_pubkey', '/delegations/{delegation_id}/pubkey',
                controller='delegations',
                conditions={'method':['GET']},
                action='get_pubkey')
    map.connect('delegation_request', '/delegations/{delegation_id}/request',
                controller='delegations',
                conditions={'method':['GET']},
                action='get_request')
    map.connect('delegation_renew', '/delegations/{delegation_id}/renew',
                controller='delegations',
                conditions={'method':['PUT']},
                action='renew')
    map.connect('delegation_attribute', '/delegations/{delegation_id}/{attr}',
                controller='delegations',
                conditions={'method':['PUT']},
                action='update_attribute')
    map.connect('/delegations/{delegation_id}/{attr}',
                controller='delegations',
                conditions={'method':['DELETE']},
                action='delete_attribute')

    map.connect('/', controller='atompub', action='index')


    return map
