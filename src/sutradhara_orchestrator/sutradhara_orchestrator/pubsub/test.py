import logging
logging.basicConfig(level=logging.DEBUG)
from broker import broker

broker.publish("mission_input", {'mission_id':123,'description':'test'})

