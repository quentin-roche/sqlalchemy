# engine/mock.py
# Copyright (C) 2005-2022 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

from __future__ import annotations

from operator import attrgetter
import typing
from typing import Any
from typing import Callable
from typing import cast
from typing import Optional
from typing import Type
from typing import Union

from . import url as _url
from .. import util


if typing.TYPE_CHECKING:
    from .base import Connection
    from .base import Engine
    from .interfaces import _CoreAnyExecuteParams
    from .interfaces import _ExecuteOptionsParameter
    from .interfaces import Dialect
    from .url import URL
    from ..sql.base import Executable
    from ..sql.ddl import DDLElement
    from ..sql.ddl import SchemaDropper
    from ..sql.ddl import SchemaGenerator
    from ..sql.schema import HasSchemaAttr


class MockConnection:
    def __init__(self, dialect: Dialect, execute: Callable[..., Any]):
        self._dialect = dialect
        self._execute_impl = execute

    engine: Engine = cast(Any, property(lambda s: s))
    dialect: Dialect = cast(Any, property(attrgetter("_dialect")))
    name: str = cast(Any, property(lambda s: s._dialect.name))

    def connect(self, **kwargs: Any) -> MockConnection:
        return self

    def schema_for_object(self, obj: HasSchemaAttr) -> Optional[str]:
        return obj.schema

    def execution_options(self, **kw: Any) -> MockConnection:
        return self

    def _run_ddl_visitor(
        self,
        visitorcallable: Type[Union[SchemaGenerator, SchemaDropper]],
        element: DDLElement,
        **kwargs: Any,
    ) -> None:
        kwargs["checkfirst"] = False
        visitorcallable(self.dialect, self, **kwargs).traverse_single(element)

    def execute(
        self,
        obj: Executable,
        parameters: Optional[_CoreAnyExecuteParams] = None,
        execution_options: Optional[_ExecuteOptionsParameter] = None,
    ) -> Any:
        return self._execute_impl(obj, parameters)


def create_mock_engine(url: URL, executor: Any, **kw: Any) -> MockConnection:
    """Create a "mock" engine used for echoing DDL.

    This is a utility function used for debugging or storing the output of DDL
    sequences as generated by :meth:`_schema.MetaData.create_all`
    and related methods.

    The function accepts a URL which is used only to determine the kind of
    dialect to be used, as well as an "executor" callable function which
    will receive a SQL expression object and parameters, which can then be
    echoed or otherwise printed.   The executor's return value is not handled,
    nor does the engine allow regular string statements to be invoked, and
    is therefore only useful for DDL that is sent to the database without
    receiving any results.

    E.g.::

        from sqlalchemy import create_mock_engine

        def dump(sql, *multiparams, **params):
            print(sql.compile(dialect=engine.dialect))

        engine = create_mock_engine('postgresql+psycopg2://', dump)
        metadata.create_all(engine, checkfirst=False)

    :param url: A string URL which typically needs to contain only the
     database backend name.

    :param executor: a callable which receives the arguments ``sql``,
     ``*multiparams`` and ``**params``.  The ``sql`` parameter is typically
     an instance of :class:`.DDLElement`, which can then be compiled into a
     string using :meth:`.DDLElement.compile`.

    .. versionadded:: 1.4 - the :func:`.create_mock_engine` function replaces
       the previous "mock" engine strategy used with
       :func:`_sa.create_engine`.

    .. seealso::

        :ref:`faq_ddl_as_string`

    """

    # create url.URL object
    u = _url.make_url(url)

    dialect_cls = u.get_dialect()

    dialect_args = {}
    # consume dialect arguments from kwargs
    for k in util.get_cls_kwargs(dialect_cls):
        if k in kw:
            dialect_args[k] = kw.pop(k)

    # create dialect
    dialect = dialect_cls(**dialect_args)  # type: ignore

    return MockConnection(dialect, executor)
