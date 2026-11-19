# C++ API

The C++ API reference lists the classes, functions and macros of the public headers,
`include/kairn/*.hpp`, with their comments. Doxygen generates it into `api/` of the built site,
where it replaces this page: the CI builds it with the site, which it keeps as the artifact `site`
of the workflow `checks.yml`. A site built without Doxygen, as by `mkdocs serve`, has only this
page; [Documentation](../developer/documentation.md#the-c-api-reference) says how to generate the
rest.
