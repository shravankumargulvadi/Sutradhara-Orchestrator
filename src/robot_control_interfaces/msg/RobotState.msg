uint8 HEALTH_OK=0
uint8 HEALTH_DEGRADED=1
uint8 HEALTH_FAILED=2

uint8 AVAIL_IDLE=0
uint8 AVAIL_BUSY=1
uint8 AVAIL_RETURNING_HOME=2
uint8 AVAIL_CHARGING=3
uint8 AVAIL_OFFLINE=4

string robot_id
string mission_id
string current_task_id

float32 x_m
float32 y_m
float32 yaw_rad
float32 z_m

float32 velocity_mps
float32 battery_pct

uint8 health_status
string[] faults
uint8 availability_status

int32 heartbeat
