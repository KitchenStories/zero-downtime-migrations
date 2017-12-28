# coding: utf-8

from __future__ import unicode_literals

import pytest
import pytz
from datetime import datetime

from django.db import models
from django.db import connections
from django.test.utils import CaptureQueriesContext
from freezegun import freeze_time

from zero_downtime_migrations.backend.schema import DatabaseSchemaEditor
from test_app.models import TestModel

pytestmark = pytest.mark.django_db
connection = connections['default']
schema_editor = DatabaseSchemaEditor


def column_classes(model):
    with connection.cursor() as cursor:
        columns = {
            d[0]: (connection.introspection.get_field_type(d[1], d), d)
            for d in connection.introspection.get_table_description(
                cursor,
                model._meta.db_table,
            )
        }
    return columns


def test_add_bool_field_no_existed_objects_success():
    columns = column_classes(TestModel)
    assert "bool_field" not in columns

    field = models.BooleanField(default=True)
    field.set_attributes_from_name("bool_field")

    with CaptureQueriesContext(connection) as ctx, schema_editor(connection=connection) as editor:
        editor.add_field(TestModel, field)

    columns = column_classes(TestModel)
    assert columns['bool_field'][0] == "BooleanField"
    queries = [query_data['sql'] for query_data in ctx.captured_queries if 'test_app' in query_data['sql']]
    expected_queries = ["SELECT IS_NULLABLE, DATA_TYPE, COLUMN_DEFAULT from information_schema.columns where table_name = 'test_app_testmodel' and column_name = 'bool_field';",
                        'ALTER TABLE "test_app_testmodel" ADD COLUMN "bool_field" boolean NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "bool_field" SET DEFAULT true',
                        "SELECT reltuples::BIGINT FROM pg_class WHERE relname = 'test_app_testmodel';",
                        'SELECT COUNT(*) FROM test_app_testmodel;',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "bool_field" SET NOT NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "bool_field" DROP DEFAULT',
                        ]
    assert queries == expected_queries


def test_add_bool_field_with_existed_object_success(test_object):
    columns = column_classes(TestModel)
    assert "bool_field" not in columns

    field = models.BooleanField(default=True)
    field.set_attributes_from_name("bool_field")
    with CaptureQueriesContext(connection) as ctx, schema_editor(connection=connection) as editor:
        editor.add_field(TestModel, field)

    columns = column_classes(TestModel)
    assert columns['bool_field'][0] == "BooleanField"
    queries = [query_data['sql'] for query_data in ctx.captured_queries if 'test_app' in query_data['sql']]
    expected_queries = ["SELECT IS_NULLABLE, DATA_TYPE, COLUMN_DEFAULT from information_schema.columns where table_name = 'test_app_testmodel' and column_name = 'bool_field';",
                        'ALTER TABLE "test_app_testmodel" ADD COLUMN "bool_field" boolean NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "bool_field" SET DEFAULT true',
                        "SELECT reltuples::BIGINT FROM pg_class WHERE relname = 'test_app_testmodel';",
                        'SELECT COUNT(*) FROM test_app_testmodel;',
                        'SELECT COUNT(*) FROM test_app_testmodel WHERE bool_field is NULL;',
                        '''
                       WITH cte AS (
                       SELECT id as pk
                       FROM test_app_testmodel
                       WHERE  bool_field is null
                       LIMIT  1000
                       )
                       UPDATE test_app_testmodel table_
                       SET bool_field = true
                       FROM   cte
                       WHERE  table_.id = cte.pk
                       ''',
                        'SELECT COUNT(*) FROM test_app_testmodel WHERE bool_field is NULL;',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "bool_field" SET NOT NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "bool_field" DROP DEFAULT',
                        ]
    assert queries == expected_queries
    sql = 'SELECT * from "test_app_testmodel" where id = %s'
    with connection.cursor() as cursor:
        cursor.execute(sql, (test_object.id, ))
        result = cursor.fetchall()
    assert result == [(test_object.id, test_object.name, True)]


def test_add_bool_field_with_existed_many_objects_success(test_object, test_object_two, test_object_three, ):
    columns = column_classes(TestModel)
    assert "bool_field" not in columns

    field = models.BooleanField(default=True)
    field.set_attributes_from_name("bool_field")
    with CaptureQueriesContext(connection) as ctx, schema_editor(connection=connection) as editor:
        editor.add_field(TestModel, field)

    columns = column_classes(TestModel)
    assert columns['bool_field'][0] == "BooleanField"
    queries = [query_data['sql'] for query_data in ctx.captured_queries if 'test_app' in query_data['sql']]
    expected_queries = ["SELECT IS_NULLABLE, DATA_TYPE, COLUMN_DEFAULT from information_schema.columns where table_name = 'test_app_testmodel' and column_name = 'bool_field';",
                        'ALTER TABLE "test_app_testmodel" ADD COLUMN "bool_field" boolean NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "bool_field" SET DEFAULT true',
                        "SELECT reltuples::BIGINT FROM pg_class WHERE relname = 'test_app_testmodel';",
                        'SELECT COUNT(*) FROM test_app_testmodel;',
                        'SELECT COUNT(*) FROM test_app_testmodel WHERE bool_field is NULL;',
                        '''
                       WITH cte AS (
                       SELECT id as pk
                       FROM test_app_testmodel
                       WHERE  bool_field is null
                       LIMIT  1000
                       )
                       UPDATE test_app_testmodel table_
                       SET bool_field = true
                       FROM   cte
                       WHERE  table_.id = cte.pk
                       ''',
                        'SELECT COUNT(*) FROM test_app_testmodel WHERE bool_field is NULL;',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "bool_field" SET NOT NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "bool_field" DROP DEFAULT',
                        ]
    assert queries == expected_queries
    sql = 'SELECT * from "test_app_testmodel" where id = ANY(%s) ORDER BY id'
    with connection.cursor() as cursor:
        cursor.execute(sql, ([test_object.id, test_object_two.id, test_object_three.id], ))
        result = cursor.fetchall()
    assert result == [(test_object.id, test_object.name, True),
                      (test_object_two.id, test_object_two.name, True),
                      (test_object_three.id, test_object_three.name, True),
                      ]


@freeze_time("2017-12-15 03:21:34", tz_offset=-3)
def test_add_datetime_field_no_existed_objects_success():
    columns = column_classes(TestModel)
    assert "datetime_field" not in columns

    field = models.DateTimeField(default=datetime.now)
    field.set_attributes_from_name("datetime_field")

    with CaptureQueriesContext(connection) as ctx, schema_editor(connection=connection) as editor:
        editor.add_field(TestModel, field)

    columns = column_classes(TestModel)
    assert columns['datetime_field'][0] == "DateTimeField"
    queries = [query_data['sql'] for query_data in ctx.captured_queries if 'test_app' in query_data['sql']]
    expected_queries = ["SELECT IS_NULLABLE, DATA_TYPE, COLUMN_DEFAULT from information_schema.columns where table_name = 'test_app_testmodel' and column_name = 'datetime_field';",
                        'ALTER TABLE "test_app_testmodel" ADD COLUMN "datetime_field" timestamp with time zone NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "datetime_field" SET DEFAULT \'2017-12-15T00:21:34+00:00\'::timestamptz',
                        "SELECT reltuples::BIGINT FROM pg_class WHERE relname = 'test_app_testmodel';",
                        'SELECT COUNT(*) FROM test_app_testmodel;',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "datetime_field" SET NOT NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "datetime_field" DROP DEFAULT',
                        ]
    assert queries == expected_queries


@freeze_time("2017-12-15 03:21:34", tz_offset=-3)
def test_add_datetime_field_with_existed_object_success(test_object):
    columns = column_classes(TestModel)
    assert "datetime_field" not in columns

    field = models.DateTimeField(default=datetime.now)
    field.set_attributes_from_name("datetime_field")
    with CaptureQueriesContext(connection) as ctx, schema_editor(connection=connection) as editor:
        editor.add_field(TestModel, field)

    columns = column_classes(TestModel)
    assert columns['datetime_field'][0] == "DateTimeField"
    queries = [query_data['sql'] for query_data in ctx.captured_queries if 'test_app' in query_data['sql']]
    expected_queries = ["SELECT IS_NULLABLE, DATA_TYPE, COLUMN_DEFAULT from information_schema.columns where table_name = 'test_app_testmodel' and column_name = 'datetime_field';",
                        'ALTER TABLE "test_app_testmodel" ADD COLUMN "datetime_field" timestamp with time zone NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "datetime_field" SET DEFAULT \'2017-12-15T00:21:34+00:00\'::timestamptz',
                        "SELECT reltuples::BIGINT FROM pg_class WHERE relname = 'test_app_testmodel';",
                        'SELECT COUNT(*) FROM test_app_testmodel;',
                        'SELECT COUNT(*) FROM test_app_testmodel WHERE datetime_field is NULL;',
                        '''
                       WITH cte AS (
                       SELECT id as pk
                       FROM test_app_testmodel
                       WHERE  datetime_field is null
                       LIMIT  1000
                       )
                       UPDATE test_app_testmodel table_
                       SET datetime_field = \'2017-12-15T00:21:34+00:00\'::timestamptz
                       FROM   cte
                       WHERE  table_.id = cte.pk
                       ''',
                        'SELECT COUNT(*) FROM test_app_testmodel WHERE datetime_field is NULL;',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "datetime_field" SET NOT NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "datetime_field" DROP DEFAULT',
                        ]
    assert queries == expected_queries
    sql = 'SELECT * from "test_app_testmodel" where id = %s'
    with connection.cursor() as cursor:
        cursor.execute(sql, (test_object.id, ))
        result = cursor.fetchall()
    assert result == [(test_object.id, test_object.name, datetime(2017, 12, 15, 0, 21, 34, tzinfo=pytz.UTC))]


@freeze_time("2017-12-15 03:21:34", tz_offset=-3)
def test_add_datetime_field_with_existed_many_objects_success(test_object, test_object_two, test_object_three, ):
    columns = column_classes(TestModel)
    assert "datetime_field" not in columns

    field = models.DateTimeField(default=datetime.now)
    field.set_attributes_from_name("datetime_field")
    with CaptureQueriesContext(connection) as ctx, schema_editor(connection=connection) as editor:
        editor.add_field(TestModel, field)

    columns = column_classes(TestModel)
    assert columns['datetime_field'][0] == "DateTimeField"
    queries = [query_data['sql'] for query_data in ctx.captured_queries if 'test_app' in query_data['sql']]
    expected_queries = ["SELECT IS_NULLABLE, DATA_TYPE, COLUMN_DEFAULT from information_schema.columns where table_name = 'test_app_testmodel' and column_name = 'datetime_field';",
                        'ALTER TABLE "test_app_testmodel" ADD COLUMN "datetime_field" timestamp with time zone NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "datetime_field" SET DEFAULT \'2017-12-15T00:21:34+00:00\'::timestamptz',
                        "SELECT reltuples::BIGINT FROM pg_class WHERE relname = 'test_app_testmodel';",
                        'SELECT COUNT(*) FROM test_app_testmodel;',
                        'SELECT COUNT(*) FROM test_app_testmodel WHERE datetime_field is NULL;',
                        '''
                       WITH cte AS (
                       SELECT id as pk
                       FROM test_app_testmodel
                       WHERE  datetime_field is null
                       LIMIT  1000
                       )
                       UPDATE test_app_testmodel table_
                       SET datetime_field = \'2017-12-15T00:21:34+00:00\'::timestamptz
                       FROM   cte
                       WHERE  table_.id = cte.pk
                       ''',
                        'SELECT COUNT(*) FROM test_app_testmodel WHERE datetime_field is NULL;',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "datetime_field" SET NOT NULL',
                        'ALTER TABLE "test_app_testmodel" ALTER COLUMN "datetime_field" DROP DEFAULT',
                        ]
    assert queries == expected_queries
    sql = 'SELECT * from "test_app_testmodel" where id = ANY(%s) ORDER BY id'
    with connection.cursor() as cursor:
        cursor.execute(sql, ([test_object.id, test_object_two.id, test_object_three.id], ))
        result = cursor.fetchall()
    assert result == [(test_object.id, test_object.name, datetime(2017, 12, 15, 0, 21, 34, tzinfo=pytz.UTC)),
                      (test_object_two.id, test_object_two.name, datetime(2017, 12, 15, 0, 21, 34, tzinfo=pytz.UTC)),
                      (test_object_three.id, test_object_three.name, datetime(2017, 12, 15, 0, 21, 34, tzinfo=pytz.UTC)),
                      ]
