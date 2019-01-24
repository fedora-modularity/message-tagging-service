class BaseConfiguration(object):
    pass


class DevConfiguration(BaseConfiguration):
    pass


class TestConfiguration(DevConfiguration):
    dry_run = True
    test = True
    test_val1 = 'abc'
