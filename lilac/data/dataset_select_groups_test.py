"""Tests for dataset.select_groups()."""

import re
from datetime import datetime

import pytest
from pytest_mock import MockerFixture

from ..schema import UUID_COLUMN, Item, field, schema
from . import dataset as dataset_module
from .dataset import BinaryOp
from .dataset_test_utils import TestDataMaker


def test_flat_data(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [
    {
      'name': 'Name1',
      'age': 34,
      'active': False
    },
    {
      'name': 'Name2',
      'age': 45,
      'active': True
    },
    {
      'age': 17,
      'active': True
    },  # Missing "name".
    {
      'name': 'Name3',
      'active': True
    },  # Missing "age".
    {
      'name': 'Name4',
      'age': 55
    }  # Missing "active".
  ]
  dataset = make_test_data(items)

  result = dataset.select_groups(leaf_path='name')
  assert result.counts == [('Name1', 1), ('Name2', 1), (None, 1), ('Name3', 1), ('Name4', 1)]

  result = dataset.select_groups(leaf_path='age', bins=[20, 50, 60])
  assert result.counts == [('1', 2), ('0', 1), (None, 1), ('2', 1)]

  result = dataset.select_groups(leaf_path='active')
  assert result.counts == [
    (True, 3),
    (False, 1),
    (None, 1),  # Missing "active".
  ]


def test_result_counts(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [
    {
      'active': False
    },
    {
      'active': True
    },
    {
      'active': True
    },
    {
      'active': True
    },
    {}  # Missing "active".
  ]
  dataset = make_test_data(items, schema=schema({UUID_COLUMN: 'string', 'active': 'boolean'}))

  result = dataset.select_groups(leaf_path='active')
  assert result.counts == [(True, 3), (False, 1), (None, 1)]


def test_list_of_structs(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [{
    'list_of_structs': [{
      'name': 'a'
    }, {
      'name': 'b'
    }]
  }, {
    'list_of_structs': [{
      'name': 'c'
    }, {
      'name': 'a'
    }, {
      'name': 'd'
    }]
  }, {
    'list_of_structs': [{
      'name': 'd'
    }]
  }]
  dataset = make_test_data(items)

  result = dataset.select_groups(leaf_path='list_of_structs.*.name')
  assert result.counts == [('a', 2), ('d', 2), ('b', 1), ('c', 1)]


def test_nested_lists(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [{
    'nested_list': [[{
      'name': 'a'
    }], [{
      'name': 'b'
    }]]
  }, {
    'nested_list': [[{
      'name': 'c'
    }, {
      'name': 'a'
    }], [{
      'name': 'd'
    }]]
  }, {
    'nested_list': [[{
      'name': 'd'
    }]]
  }]
  dataset = make_test_data(items)

  result = dataset.select_groups(leaf_path='nested_list.*.*.name')
  assert result.counts == [('a', 2), ('d', 2), ('b', 1), ('c', 1)]


def test_nested_struct(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [
    {
      'nested_struct': {
        'struct': {
          'name': 'c'
        }
      }
    },
    {
      'nested_struct': {
        'struct': {
          'name': 'b'
        }
      }
    },
    {
      'nested_struct': {
        'struct': {
          'name': 'a'
        }
      }
    },
  ]
  dataset = make_test_data(items)

  result = dataset.select_groups(leaf_path='nested_struct.struct.name')
  assert result.counts == [('c', 1), ('b', 1), ('a', 1)]


def test_named_bins(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [{
    'age': 34,
  }, {
    'age': 45,
  }, {
    'age': 17,
  }, {
    'age': 80
  }, {
    'age': 55
  }, {
    'age': float('nan')
  }]
  dataset = make_test_data(items)

  result = dataset.select_groups(
    leaf_path='age',
    bins=[
      ('young', None, 20),
      ('adult', 20, 50),
      ('middle-aged', 50, 65),
      ('senior', 65, None),
    ])
  assert result.counts == [('adult', 2), ('young', 1), ('senior', 1), ('middle-aged', 1), (None, 1)]


def test_schema_with_bins(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [{
    'age': 34,
  }, {
    'age': 45,
  }, {
    'age': 17,
  }, {
    'age': 80
  }, {
    'age': 55
  }, {
    'age': float('nan')
  }]
  data_schema = schema({
    UUID_COLUMN: 'string',
    'age': field(
      'float32',
      bins=[
        ('young', None, 20),
        ('adult', 20, 50),
        ('middle-aged', 50, 65),
        ('senior', 65, None),
      ])
  })
  dataset = make_test_data(items, data_schema)

  result = dataset.select_groups(leaf_path='age')
  assert result.counts == [('adult', 2), ('young', 1), ('senior', 1), ('middle-aged', 1), (None, 1)]


def test_filters(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [
    {
      'name': 'Name1',
      'age': 34,
      'active': False
    },
    {
      'name': 'Name2',
      'age': 45,
      'active': True
    },
    {
      'age': 17,
      'active': True
    },  # Missing "name".
    {
      'name': 'Name3',
      'active': True
    },  # Missing "age".
    {
      'name': 'Name4',
      'age': 55
    }  # Missing "active".
  ]
  dataset = make_test_data(items)

  # active = True.
  result = dataset.select_groups(leaf_path='name', filters=[('active', BinaryOp.EQUALS, True)])
  assert result.counts == [('Name2', 1), (None, 1), ('Name3', 1)]

  # age < 35.
  result = dataset.select_groups(leaf_path='name', filters=[('age', BinaryOp.LESS, 35)])
  assert result.counts == [('Name1', 1), (None, 1)]

  # age < 35 and active = True.
  result = dataset.select_groups(
    leaf_path='name', filters=[('age', BinaryOp.LESS, 35), ('active', BinaryOp.EQUALS, True)])
  assert result.counts == [(None, 1)]


def test_datetime(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [
    {
      UUID_COLUMN: '1',
      'date': datetime(2023, 1, 1)
    },
    {
      UUID_COLUMN: '2',
      'date': datetime(2023, 1, 15)
    },
    {
      UUID_COLUMN: '2',
      'date': datetime(2023, 2, 1)
    },
    {
      UUID_COLUMN: '4',
      'date': datetime(2023, 3, 1)
    },
    {
      UUID_COLUMN: '5',
      # Missing datetime.
    }
  ]
  dataset = make_test_data(items)
  result = dataset.select_groups('date')
  assert result.counts == [(datetime(2023, 1, 1), 1), (datetime(2023, 1, 15), 1),
                           (datetime(2023, 2, 1), 1), (datetime(2023, 3, 1), 1), (None, 1)]


def test_invalid_leaf(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [
    {
      'nested_struct': {
        'struct': {
          'name': 'c'
        }
      }
    },
    {
      'nested_struct': {
        'struct': {
          'name': 'b'
        }
      }
    },
    {
      'nested_struct': {
        'struct': {
          'name': 'a'
        }
      }
    },
  ]
  dataset = make_test_data(items)

  with pytest.raises(
      ValueError, match=re.escape("Leaf \"('nested_struct',)\" not found in dataset")):
    dataset.select_groups(leaf_path='nested_struct')

  with pytest.raises(
      ValueError, match=re.escape("Leaf \"('nested_struct', 'struct')\" not found in dataset")):
    dataset.select_groups(leaf_path='nested_struct.struct')

  with pytest.raises(
      ValueError,
      match=re.escape("Path ('nested_struct', 'struct', 'wrong_name') not found in schema")):
    dataset.select_groups(leaf_path='nested_struct.struct.wrong_name')


def test_too_many_distinct(make_test_data: TestDataMaker, mocker: MockerFixture) -> None:
  too_many_distinct = 5
  mocker.patch(f'{dataset_module.__name__}.TOO_MANY_DISTINCT', too_many_distinct)

  items: list[Item] = [{'feature': str(i)} for i in range(too_many_distinct + 10)]
  dataset = make_test_data(items)

  res = dataset.select_groups('feature')
  assert res.too_many_distinct is True
  assert res.counts == []


def test_auto_bins_for_float(make_test_data: TestDataMaker) -> None:
  items: list[Item] = [{'feature': float(i)} for i in range(5)] + [{'feature': float('nan')}]
  dataset = make_test_data(items)

  res = dataset.select_groups('feature')
  assert res.counts == [('0', 1), ('3', 1), ('7', 1), ('11', 1), ('14', 1), (None, 1)]
  assert res.too_many_distinct is False
  assert res.bins