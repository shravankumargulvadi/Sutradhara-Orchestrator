import threading
from typing import Callable, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class MessageBroker:
    """
    A simple thread-safe in-process message broker for topic-based pub/sub.
    This replaces the ROS2 pub/sub system during development and testing on macOS.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = threading.Lock()

    def publish(self, topic: str, message: Any) -> None:
        """
        Publishes a message to all subscribers of a specific topic.
        """
        with self._lock:
            if topic not in self._subscribers:
                logger.debug(f"Topic {topic} has no subscribers.")
                return
            
            # Create a copy of the list of subscribers to avoid issues if a subscriber
            # modifies the list during iteration.
            callbacks = self._subscribers[topic][:]

        for callback in callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in subscriber callback for topic {topic}: {e}")

    def subscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        """
        Subscribes a callback function to a specific topic.
        """
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            
            if callback not in self._subscribers[topic]:
                self._subscribers[topic].append(callback)
                logger.info(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        """
        Unsubscribes a callback function from a specific topic.
        """
        with self._lock:
            if topic in self._subscribers:
                if callback in self._subscribers[topic]:
                    self._subscribers[topic].remove(callback)
                    logger.info(f"Unsubscribed from topic: {topic}")
                
                if not self._subscribers[topic]:
                    del self._subscribers[topic]

# Global instance for easy access (mocking a singleton broker)
broker = MessageBroker()
