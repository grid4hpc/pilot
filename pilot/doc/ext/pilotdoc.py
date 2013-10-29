# -*- encoding: utf-8 -*-

u"""

Расширения, используемые для документации Pilot

"""

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx import addnodes
from sphinx.domains import Domain, ObjType
from sphinx.locale import l_, _
from sphinx.roles import XRefRole, emph_literal_role
from sphinx.directives import ObjectDescription
from sphinx.util.nodes import make_refnode

class AttrDirective(ObjectDescription):
    option_spec = {
        'noindex': directives.flag,
        'type': directives.unchanged_required,
        'required': directives.flag,
        'comment': directives.unchanged_required,
    }

    @classmethod
    def make_target_name(klass, name):
        raise NotImplementedError

    @classmethod
    def make_index_text(klass, name):
        raise NotImplementedError

    def add_target_and_index(self, name, sig, signode):
        targetname = self.make_target_name(name)
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)

            objects = self.env.domaindata['pilot']['objects']
            key = (self.objtype, name)
            if key in objects:
                self.env.warn(self.env.docname, 
                              'duplicate description of %s %s, ' %
                              (self.objtype, name) +
                              'other instance in ' +
                              self.env.doc2path(objects[key]),
                              self.lineno)
            objects[key] = self.env.docname
            
        indextext = self.make_index_text(name)
        self.indexnode['entries'].append(('single', indextext,
                                          targetname, targetname))

    def handle_signature(self, sig, signode):
        attrtype = self.options.get('type', _(u"объект"))
        typedef = self.options.get('type', 'str').split()
        typemap = {
            'object': u"объект",
            'int': u"целое число",
            'str': u"строка",
            'list': u"список",
            'bool': u"истина/ложь",
        }
        if typedef[0] not in typemap:
            self.env.warn(self.env.docname, "%d: Unknown pilot attr type: %s, defaulting to object" % (self.env.lineno, typedef[0]))
            typedef[0] = 'object'
            
        t = u", " + typemap[typedef[0]]

        if typedef[0] == 'list':
            if len(typedef) > 1:
                t += u", тип элемента: %s" % typemap[typedef[1]]
            if len(typedef) > 2:
                t += u", не менее %s элемента" % typedef[2]

        if 'comment' in self.options:
            t += u", %s" % self.options['comment']
        
        if 'required' not in self.options:
            t += u", опциональный параметр"

        signode += nodes.strong(sig, sig)
        signode += nodes.emphasis(t, t)
        return sig

class JobAttrDirective(AttrDirective):
    @classmethod
    def make_target_name(klass, name):
        return "pilot-job-%s" % name

    @classmethod
    def make_index_text(klass, name):
        return u"%s; атрибут описания задания %s" % (name, name)

class TaskAttrDirective(AttrDirective):
    @classmethod
    def make_target_name(klass, name):
        return "pilot-task-%s" % name

    @classmethod
    def make_index_text(klass, name):
        return u"%s; атрибут описания задачи %s" % (name, name)

class ReqAttrDirective(AttrDirective):
    @classmethod
    def make_target_name(klass, name):
        return "pilot-requirements-%s" % name

    @classmethod
    def make_index_text(klass, name):
        return u"%s; атрибут описания требований к ресурсам %s" % (name, name)

class PilotDocDomain(Domain):
    u"""
    Домен документации pilot
    """
    name = "pilot"
    label = u"Объекты pilot"

    object_types = {
        'jobattr': ObjType(l_(u"атрибут описания задания"), 'jobattr'),
        'taskattr': ObjType(l_(u"атрибут описания задачи"), 'taskattr'),
        'reqattr': ObjType(l_(u"атрибут описания требований к ресурсам"), 'reqattr'),
    }
    directives = {
        'jobattr': JobAttrDirective,
        'taskattr': TaskAttrDirective,
        'reqattr': ReqAttrDirective,
    }
    roles = {
        'jobattr': XRefRole(),
        'taskattr': XRefRole(),
        'reqattr': XRefRole(),
    }
    initial_data = {
        'objects': {}
    }

    def get_objclass(self, objtype):
        return self.directives[objtype]

    def clear_doc(self, docname):
        objects = self.data['objects']
        for (typ, name), doc in objects.items():
            if doc == docname:
                objects.pop((typ, name))

    def get_type_name(self, objtype):
        return objtype.lname

    def get_objects(self):
        for (typ, name), doc in self.data['objects'].iteritems():
            anchor = self.get_objclass(typ).make_target_name(name)
            yield name, name, typ, doc, anchor, 1

    def resolve_xref(self, env, fromdocname, builder, typ, target,
                     node, contnode):
        objects = self.data['objects']
        objtypes = self.objtypes_for_role(typ)
        for objtype in objtypes:
            if (objtype, target) in objects:
                klass = self.get_objclass(objtype)
                return make_refnode(builder, fromdocname,
                                    objects[objtype, target],
                                    klass.make_target_name(target),
                                    contnode, target + ' ' + objtype)
           

def setup(app):
    app.add_domain(PilotDocDomain)
