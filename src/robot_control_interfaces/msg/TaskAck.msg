uint8 ACCEPTED=0
uint8 REJECTED=1
uint8 ACK_CANCELLED=2

uint8 REASON_NONE=0
uint8 REASON_LOW_BATTERY=1
uint8 REASON_CAPABILITY_MISSING=2
uint8 REASON_BUSY=3
uint8 REASON_TARGET_INVALID=4
uint8 REASON_SAFETY_CONSTRAINT=5
uint8 REASON_INTERNAL_ERROR=6

string mission_id
string robot_id
string task_id
string command_id
uint8 decision
uint8 reject_reason_code
string reject_reason_detail
