
import threading

def thread_func(func):
    """
    この関数を噛ませると関数を非同期で動作させる
    thread_func(some_func)()
    """
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()
    return wrapper