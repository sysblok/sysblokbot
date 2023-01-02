import threading

create_lock = threading.Lock()


class Singleton:
    """
    Singleton base class.
    To ease introspection, client classes supposed to be singletons.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with create_lock:
                cls._instance = object.__new__(cls)
                cls._instance._was_initialized = False
        return cls._instance

    def was_initialized(self):
        """
        Use this check in the beginning of __init__()
        to initialize instance only once.
        """
        if self._was_initialized:
            return True
        self._was_initialized = True
        return False

    @classmethod
    def drop_instance(cls):
        """
        To be used in testing purposes (testing proper instance creation)
        """
        cls._instance = None
