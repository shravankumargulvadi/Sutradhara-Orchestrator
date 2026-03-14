import pytest
from sutradhara_orchestrator.pubsub.broker import MessageBroker

def test_publish_subscribe():
    broker = MessageBroker()
    received_messages = []

    def callback(msg):
        received_messages.append(msg)

    broker.subscribe("test_topic", callback)
    broker.publish("test_topic", "hello")
    
    assert received_messages == ["hello"]

def test_multiple_subscribers():
    broker = MessageBroker()
    sub1_msgs = []
    sub2_msgs = []

    broker.subscribe("topic-a", lambda m: sub1_msgs.append(m))
    broker.subscribe("topic-a", lambda m: sub2_msgs.append(m))
    
    broker.publish("topic-a", "data")
    
    assert sub1_msgs == ["data"]
    assert sub2_msgs == ["data"]

def test_unsubscribe():
    broker = MessageBroker()
    msgs = []
    def cb(m): msgs.append(m)

    broker.subscribe("t", cb)
    broker.publish("t", "1")
    broker.unsubscribe("t", cb)
    broker.publish("t", "2")
    
    assert msgs == ["1"]
