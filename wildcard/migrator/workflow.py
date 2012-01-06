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
            old_state = currentstatus['review_state']
            new_state = status and status['review_state'] or None
            if status and old_state != new_state:
                portal_workflow = getToolByName(obj, 'portal_workflow')
                chain = portal_workflow.getChainFor(obj)[0]

                if chain[0] == '(Default)':
                    chain = portal_workflow.getDefaultChain()

                workflow = portal_workflow[chain]
                portal_workflow.setStatusOf(chain[0], obj, status)
                auto_transition = workflow._findAutomaticTransition(obj,
                    workflow._getWorkflowStateOf(obj))
                if auto_transition is not None:
                    workflow._changeStateOf(obj, auto_transition)
                else:
                    workflow.updateRoleMappingsFor(obj)

    def set(self, state, action):
        return self._set(self.obj, state, action)
addMigrator(WorkflowStateMigrator)


class WorkflowHistoryMigrator(BaseMigrator):
    title = 'Workflow History'
    _type = 'object'

    @classmethod
    def _get(kls, obj):
        return getattr(obj, 'workflow_history', None)

    @classmethod
    def _set(kls, obj, data):
        if data:
            obj.workflow_history = PersistentDict(data)
addMigrator(WorkflowHistoryMigrator)
