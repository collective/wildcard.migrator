-Introduction
============


Site migrations
---------------

- html filtering
- transform settings
- redirection storage(or maybe for each content)


Content
-------

- archetypes fields(X)
    - need to convert reference objects(x)
- properties(X)
- owner(x)
- workflow state(x)
- annotations(x)
- interfaces(x)
- local roles(x)
- permissions(XXX) - should not have to do these, workflows should take care of this
- history(X)

- syndication information?(x)
- UIDs!!!(x)
- portlets(use GS code)(x)
- placeful workflow

ToDo
====

- batching to make it faster??
- use GS for as many as possible
    - workflow(X)
        - workflow_history on content(X)
    - permissions
        - NEED TO FIGURE OUT HOW TO EXPORT
          CONTENT PERMISSIONS
    - CONTENT(redo core content stuff)
        - use manage_getwhatever

- deferred archetype value setter
    - very large files that don't serialize well.
