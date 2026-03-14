import time
import pytest
from sutradhara_orchestrator.orchestrator.world_state_manager import WorldStateManager
from sutradhara_orchestrator.simulation.robot import SimulatedUAV, SimulatedUGV
from sutradhara_orchestrator.pubsub.broker import broker

def test_robot_discovery():
    wsm = WorldStateManager()
    uav = SimulatedUAV("uav_1")
    
    # Manually trigger advertisement
    uav.advertise()
    
    time.sleep(0.1)
    robot = wsm.get_robot("uav_1")
    assert robot is not None
    assert robot.capabilities.platform == 0 # UAV

def test_robot_state_tracking():
    wsm = WorldStateManager()
    uav = SimulatedUAV("uav_test")
    
    # Start robot thread
    uav.start()
    
    # Wait for first state update
    time.sleep(1.5)
    
    summary = wsm.get_world_summary()
    assert summary["count"] == 1
    assert summary["robots"][0]["robot_id"] == "uav_test"
    
    uav.stop()

def test_heartbeat_timeout():
    wsm = WorldStateManager(heartbeat_timeout_s=0.5)
    uav = SimulatedUAV("uav_timeout")
    
    uav.start()
    
    # Wait for first update but check BEFORE it times out
    time.sleep(0.3)
    assert len(wsm.get_active_robots()) == 1
    
    # Stop robot and wait for it to time out
    uav.stop()
    time.sleep(0.8)
    assert len(wsm.get_active_robots()) == 0
