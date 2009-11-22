import sys
import time
import thread
from threading import Lock

class BlockingList(list):
    """
    Provide a list mechanism that also has 'inverse' semaphore semnatics for the
    empty state.

    This is not for thread synchronization; this is not a thread-safe class!
    Do your own thread safety.
    
    That said, this can only be useful in a multi-threaded program.

    Thread 1:
        obj = BlockingList()
        while True:
            obj.acquire()
            while len(obj):
                for item in obj:
                    do_stuff(item)
            obj.release()

    Thread 2:
        obj.append(item)
        time.sleep(5)
        obj.remove(item) # This is currently the only 'remove' semantic
        supported

    Thread 1 will block while the list is empty but is not in a busy-wait state.
    """
    def __init__(self, *args, **kwargs):
        list.__init__(self, *args, **kwargs)
        self.lock = Lock()
        self.lock_self()
        self.acquire = self.lock.acquire
        self.release = self.lock.release

    def acquire(self, *args):
        return self.lock.acquire(*args)

    def release(self):
        return self.lock.release()

    def append(self, thing):
        list.append(self, thing)
        if self.lock.locked():
            self.release()

    def remove(self, thing):
        if len(self) == 1:
            self.acquire()
        list.remove(self, thing)

    def lock_self(self):
        """ Lock as needed """
        if len(self) == 0:
            self.acquire()

def main():
    l = BlockingList()
    def foo():
        while True:
            l.acquire()
            sys.stdout.write('foo - blocking list lock acquired - %d\n' % len(l))
            while len(l):

                sys.stdout.write('foo - l contents:')
                for s in l:
                    sys.stdout.write(s)
                    sys.stdout.write(', ')
                sys.stdout.write('\n')
                time.sleep(1)
            l.release()

    def bar():
        sys.stdout.write('bar sleeping\n')
        time.sleep(2)
        sys.stdout.write('bar adding\n')
        s = 'data'
        l.append(s)
        l.append('hi')
        time.sleep(.5)
        l.remove(s)
        time.sleep(.5)
        l.append('bye')
        l.remove('hi')
        time.sleep(3)


    thread.start_new_thread(lambda :foo(), ())
    bar()

if __name__ == "__main__":
    main()
