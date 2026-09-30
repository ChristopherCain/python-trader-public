from pythontrader.scheduler.queue import ScheduledTask, TaskQueue


def test_due_tasks():
    q = TaskQueue()
    q.put(ScheduledTask(2, "b"))
    q.put(ScheduledTask(1, "a"))
    assert [x.name for x in q.due(1.5)] == ["a"]
