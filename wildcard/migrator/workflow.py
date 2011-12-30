from persistent.dict import PersistentDict
from wildcard.migrator import addMigrator
from Products.CMFCore.utils import getToolByName
# use generic setup to import/export this...
from wildcard.migrator import BaseMigrator


def getWorkflowStatus(obj):
    workflowTool = getToolByName(obj, "portal_workflow")
    # Returns workflow state object
    chain = workflowTool.getChainFor(obj)
    if not chain:
        return None
    return workflowTool.getStatusOf(chain[0], obj)


class WorkflowStateMigrator(BaseMigrator):
    title = "Workflow State"
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        status = getWorkflowStatus(obj)
        # Plone workflows use variable called "review_state" to store state id
        # of the object state
        return status

    @classmethod
    def _set(kls, obj, status):
        if status:
            currentstatus = getWorkflowStatus(obj)
            if status and currentstatus['review_state'] != \
                                            status['review_state']:
                workflowTool = getToolByName(obj, "portal_workflow")
                return workflowTool.doActionFor(obj,
                    status['action'], comment=status.get('comment', ''))

    def set(self, state, action):
        return self._set(self.obj, state, action)
addMigrator(WorkflowStateMigrator)


class WorkflowHistoryMigrator(BaseMigrator):
    title = 'Workflow History'
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        return obj.workflow_history

    @classmethod
    def _set(kls, obj, data):
        obj.workflow_history = PersistentDict(data)
addMigrator(WorkflowHistoryMigrator)
