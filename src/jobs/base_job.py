import logging
from typing import Callable

from ..app_context import AppContext

logger = logging.getLogger(__name__)


class BaseJob:
    @classmethod
    def execute(
        cls,
        app_context: AppContext,
        send: Callable[[str], None] = lambda msg: None,
        called_from_handler=False,
        args=None,
        kwargs=None,
    ):
        """
        Not intended to be overridden.
        Default send function does nothing with all send(...) statements.
        """
        module = cls.__name__
        if cls._usage_muted():
            logging_func = logger.info
        else:
            logging_func = logger.usage

        try:
            logging_func(f"Job {module} started...")
            import inspect
            import asyncio

            # This returns either a result (sync) or coroutine (async)
            res = cls._execute(
                app_context,
                send,
                called_from_handler,
                *args if args else [],
                **kwargs if kwargs else {},
            )

            if inspect.isawaitable(res):
                try:
                    # Check if we are running in the main event loop (e.g. called from Handler)
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        # We are in an async context (Handler).
                        # Return the coroutine so the caller (asyncify) can await it.
                        return res
                except RuntimeError:
                    # No running loop. We are likely in a Scheduler thread.
                    pass

                # If we are here, we need to run the coroutine synchronously/threadsafe
                # The coroutine likely uses TgClient which is bound to the Main Loop.
                # So we must schedule it on the Main Loop and wait for result.

                # Check if app_context has tg_client and valid loop
                if hasattr(app_context, "tg_client") and hasattr(
                    app_context.tg_client, "api_client"
                ):
                    main_loop = app_context.tg_client.api_client.loop
                    if main_loop and main_loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(res, main_loop)
                        return future.result()

                # Fallback (e.g. testing or no loop running): run locally
                return asyncio.run(res)

            logging_func(f"Job {module} finished")
        except Exception as e:
            # should not raise exception, so that schedule module won't go mad retrying
            logging.exception(f"Could not run job {module}", exc_info=e)

    @staticmethod
    def _execute(
        app_context: AppContext,
        send: Callable[[str], None],
        called_from_handler=False,
        *args,
        **kwargs,
    ):
        """
        Must be overridden.
        *args are intended for calling from handlers directly,
        **kwargs are read from job config
        """
        raise NotImplementedError("Job does not have _execute method implemented")

    @classmethod
    def __str__(cls):
        return cls.__module__

    @staticmethod
    def _usage_muted():
        return False
