#!/usr/bin/env python3

from os import cpu_count
from queue import Queue, Empty
from threading import Thread, Event
from uuid import uuid4 as gen_uid
from warnings import warn
from enum import Enum, unique
from functools import partial

from debug import debug_method_info

@unique
class EventType(Enum):
    """
    # parent event:   distribute child event
    # child event:    process one
    # feedback event: return child event result
    # final event:    complete parent work
    """
    parent = 1
    child = 2
    feedback = 3
    final = 4

class EventWrapper:
    def __init__(self, master, etype, eid, handler, *args, **kwargs):
        """
        master: EventQueue
        etype: EventType
        eid: Unique id for group of events
        handler: event handler to be invoked
        """
        self._type = etype
        self._id = eid
        self._master = master
        try:
            self._handler = partial(handler, *args, **kwargs)
        except TypeError:
            self._handler = None

    def dispatch(self):
        if self._handler is not None:
            return self._handler()

    @property
    def getType(self):
        return self._type

    @property
    def getId(self):
        return self._id

@unique
class QueueStatus(Enum):
    un_init = 0 # un-initialized
    init = 1 # distributing event
    waiting = 2 # distributed, waiting final
    final = 3 # all children is done

class EventQueue:
    """ Hold queue of events
    call setChildren to set children iter
    call startEvents to start
    method can be overrided: createQueue, on_started, on_child_process,
        on_child_done, on_finished
    """
    @debug_method_info()
    def __init__(self, children = ()):
        self._child_event_count = 0
        self._child_event_done_count = 0
        self.queue_router.update(self.createQueue())
        self.setChildren(children)
        self._stop_event = Event()
        self._worker_router = {
                EventType.parent:   self._worker_parent,
                EventType.child :   self._worker_child,
                EventType.feedback: self._worker_feedback,
                EventType.final :   self._worker_final,
                }

    @debug_method_info()
    def __del__(self):
        self._stop_event.set()
        for queue in self._queue_router.values():
            self.remove_queue(queue)

    def remove_queue(self, Q):
        # ref: http://stackoverflow.com/questions/6517953/clear-all-items-from-the-queue
        with Q.mutex:
            for ele in filter(lambda x: x.getId == self.task_id, Q.queue):
                Q.queue.remove(ele)
                Q.task_done()

    def createQueue(self):
        """ create alternative Queue, to be overrided
        """
        return {}

    def _wrap_event(self, etype, handler, *args, **kwargs):
        return EventWrapper(self, etype, self.task_id, handler, *args, **kwargs)

    @property
    def queue_router(self):
        if not hasattr(self, "_queue_router"):
            self._queue_router = { et: Queue() for et in EventType }
            print("queue count:", len(self._queue_router))
        return self._queue_router

    @property
    def state(self):
        if not hasattr(self, "_state"):
            self._state = QueueStatus.un_init
        return self._state

    @property
    def task_id(self):
        if not hasattr(self, "_task_id"):
            self._task_id = gen_uid()
        return self._task_id

    @property
    def queue_parent(self):
        return self._queue_router[EventType.parent]

    @property
    def queue_child(self):
        return self._queue_router[EventType.child]

    @property
    def queue_feedback(self):
        return self._queue_router[EventType.feedback]

    @property
    def queue_final(self):
        return self._queue_router[EventType.final]

    @debug_method_info()
    def _worker(self, queue):
        while not self._stop_event.is_set():
            try:
                event = queue.get(timeout=1)
            except Empty:
                continue
            if event.getId == self.task_id:
                self._dispatch(event)
                queue.task_done()
            else:
                queue.put(event)
        print("quit worker")

    @debug_method_info()
    def _worker_parent(self, event):
        event.dispatch()

    @debug_method_info()
    def _put_child(self, chid):
        self._child_event_count += 1
        chandler = self.on_child_process
        cevent = self._wrap_event(EventType.child, chandler, chid)
        self._queue_router[EventType.child].put(cevent)

    @debug_method_info()
    def _worker_child(self, event):
        result = event.dispatch()
        self._put_feedback(result)

    @debug_method_info()
    def _put_feedback(self, result):
        fevent = self._wrap_event(EventType.feedback, self._feedback_process, result)
        self.queue_feedback.put(fevent)

    @debug_method_info()
    def _feedback_process(self, result):
        """ check child process
        """
        self._child_event_done_count += 1
        if self.state == QueueStatus.waiting and \
                self._child_event_done_count == self._child_event_count:
                    self._state = QueueStatus.final
                    print("all children finished")
        self.on_child_done(result)
        if self.state == QueueStatus.final:
            self._put_final()

    @debug_method_info()
    def _put_final(self):
        fievent = self._wrap_event(EventType.final, self._final_process)
        self.queue_final.put(fievent)

    @debug_method_info()
    def _worker_feedback(self, event):
        print("_worker_feedback", event)
        event.dispatch()

    @debug_method_info()
    def _worker_final(self, event):
        print("_worker_final", event)
        event.dispatch()

    @debug_method_info()
    def _dispatch(self, event):
        self._worker_router[event.getType](event)

    @debug_method_info()
    def startEvents(self):
        """ Process events
        """
        if self.state != QueueStatus.un_init:
            raise RuntimeError("At present the queue can only be started once!")

        self._thread_parent = Thread(target = self._worker, args = ( self.queue_parent,))
        self._thread_parent.start()

        self._child_worker_count = 1 if cpu_count() <= 1 else cpu_count() - 1
        self._thread_children = [
                Thread(target = self._worker, args = ( self.queue_child,)) \
                        for i in range(self._child_worker_count) ]
        [ x.start() for x in self._thread_children ]

        self._thread_feedback = Thread(target = self._worker, args = ( self.queue_feedback,))
        self._thread_feedback.start()

        self._thread_final = Thread(target = self._worker, args = ( self.queue_final,))
        self._thread_final.start()

        self._put_parent()
        self.on_started()

    @debug_method_info()
    def on_started(self):
        """ Hook after queue started
        """
        pass

    @debug_method_info()
    def _put_parent(self):
        """ Starting queue, put parent event
        """
        pevent = self._wrap_event(EventType.parent, self._parent_process)
        self.queue_parent.put(pevent)

    @debug_method_info()
    def _parent_process(self):
        """ Distributing child event
        """
        self._state = QueueStatus.init
        for child in self._children:
            self._put_child(child)
        self._state = QueueStatus.waiting

    def setChildren(self, childIter):
        if childIter is None:
            self._children = ()
            return
        try:
            self._children = iter(childIter)
        except TypeError:
            self._children = iter(childIter,)

  #  def _get_child(self):
  #      """ Distribute child events ...
  #      """
  #      try:
  #          child = next(self._children)
  #          yield self._put_child(child)
  #      except StopIteration:
  #          return

    @debug_method_info()
    def on_child_process(self, child):
        """ Child event that can be executed concurrently
        """
        pass

    @debug_method_info()
    def on_child_done(self, result):
        """ Give feedback when one child process finished
        """
        pass

    @debug_method_info()
    def _final_process(self):
        self.on_finished()
        self._stop_event.set()

    @debug_method_info()
    def on_finished(self):
        """ Hook when all events are done
        """
        pass
