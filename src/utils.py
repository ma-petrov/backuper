import functools
import itertools
import math
import threading
import time
import typing

_P = typing.ParamSpec("_P")

G = "\033[32m"
Y = "\033[33m"
_ = "\033[0m"


class IterableSized[T](typing.Iterable[T], typing.Sized):
    pass


def print_inline(text: str) -> None:
    """Вывод в консоль без переноса строки."""

    print(text if text.startswith("\r") else "\r" + text, end="", flush=True)


def progress[T](
    iterable: IterableSized[T],
    description: str = "Progress",
    bar_size: int = 20,
    update_interval: float = 0.2,
) -> typing.Generator[T]:
    """Добавляет отрисовку progress бара во время работы функции.

    Пример, если есть функция, которая возвращает ответы http-клиента по мере
    их готовности:

    >>> for response in progress(make_requests(request_jsons))
    ...     # do somthing
    """

    start = progress_last_update = time.time()
    total = len(iterable)

    for step, item in enumerate(iterable):

        if time.time() - progress_last_update > update_interval:
            progress_last_update = time.time()

            progress = math.floor(((step + 1) / total) * bar_size)
            bar = "*" * progress + "-" * (bar_size - progress)

            remaining = (time.time() - start) / (step + 1) * (total - step - 1)
            remaining_str = time.strftime("%H:%M:%S", time.gmtime(remaining))
            statisctic = f"{step + 1}/{total} remaining: {remaining_str}"

            print_inline(f"{Y}{description}{_} [{G}{bar}{_}] {statisctic}")

        yield item


def spinner[T](
    description: str = "Thinking...",
    update_interval: float = 0.2,
) -> typing.Callable[[typing.Callable[_P, T]], typing.Callable[_P, T]]:
    """Добавляет отрисовку spinner'а во время выполнения функции."""

    def decorator(func: typing.Callable[_P, T]) -> typing.Callable[_P, T]:

        def draw_spinner(stop_event: threading.Event) -> None:
            """Рисует в консоли спиннер, пока не получит stop event."""

            for spinner in itertools.cycle("|/-\\"):
                if stop_event.is_set():
                    break

                print_inline(f"{Y}{description}{_} {G}{spinner}{_}")
                time.sleep(update_interval)

        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> T:

            # Запуск отрисовки спиннера в отдельном потоке.
            stop_event = threading.Event()
            thread = threading.Thread(
                target=draw_spinner,
                args=(stop_event,),
                daemon=True,
            )
            thread.start()

            # Выполнение основной функци
            try:
                return func(*args, **kwargs)
            finally:
                stop_event.set()
                thread.join()

        return wrapper
    return decorator
