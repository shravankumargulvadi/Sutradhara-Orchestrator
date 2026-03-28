uint8 PLATFORM_UAV=0
uint8 PLATFORM_AMR=1

uint8 TASK_INSPECT=0
uint8 TASK_VERIFY=1
uint8 TASK_REVISIT=2
uint8 TASK_PATROL=3
uint8 TASK_RETURN_HOME=4

string robot_id
uint8 platform
float32 max_speed_mps
float32 max_run_time_s
string[] sensors
uint8[] task_types_supported
